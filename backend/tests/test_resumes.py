"""简历模块测试：上传校验 / 解析 / 越权隔离 / 历史对比。"""
import io
import uuid

from docx import Document

from app.models.resume_analysis import (
    STATUS_COMPLETED,
    STATUS_PROCESSING,
    ResumeAnalysis,
)

def make_docx_bytes(text: str) -> bytes:
    """用 python-docx 现场造一个合法 docx，走真实解析链路。"""
    buf = io.BytesIO()
    doc = Document()
    doc.add_paragraph(text)
    doc.save(buf)
    return buf.getvalue()


def _create_completed_record(db_session, user_id: int, overall: int = 80) -> int:
    """直接往测试库写一条 completed 记录（带合法 result_json），绕过 AI 调用。"""
    record = ResumeAnalysis(
        user_id=user_id,
        filename=f"fake-{uuid.uuid4().hex[:6]}.docx",
        stored_filename=f"{uuid.uuid4().hex}.docx",
        file_ext=".docx",
        content_text="测试简历内容",
        status=STATUS_COMPLETED,
        result_json={
            "completeness": 70,
            "completeness_issues": ["缺少教育经历"],
            "strengths": ["有量化数据"],
            "weaknesses": ["技能罗列无重点"],
            "suggestions": ["补充项目背景"],
            "overall_score": overall,
            "summary": "整体尚可",
            "jd_match": {
                "score": 66,
                "matched": ["Python"],
                "missing": ["Docker"],
            },
        },
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record.id


def _get_user_id(client, headers: dict) -> int:
    return client.get("/api/users/me", headers=headers).json()["id"]


# ---------- 上传 ----------


def test_upload_requires_auth(client):
    resp = client.post(
        "/api/resumes/upload",
        files={"file": ("x.docx", make_docx_bytes("hello"), "application/octet-stream")},
    )
    assert resp.status_code == 401


def test_upload_docx_parses_text(client, auth_headers):
    text = "张三，Python 工程师，5 年经验，熟悉 FastAPI / MySQL / Redis"
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={
            "file": (
                "resume.docx",
                make_docx_bytes(text),
                "application/octet-stream",
            )
        },
        data={"job_description": "要求熟悉 Python 后端"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["filename"] == "resume.docx"
    assert body["job_description"] == "要求熟悉 Python 后端"


def test_upload_rejects_txt_extension(client, auth_headers):
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_fake_docx(client, auth_headers):
    """改扩展名的假文件：白名单放行，但解析兜底会拒绝。"""
    resp = client.post(
        "/api/resumes/upload",
        headers=auth_headers,
        files={"file": ("fake.docx", b"this is not a real docx", "application/octet-stream")},
    )
    assert resp.status_code == 400


# ---------- 越权隔离 ----------


def test_cross_user_isolation(client, db_session, make_user):
    """水平越权防护：A 的 token 读不到 B 的记录。"""
    headers_a = make_user()
    headers_b = make_user()
    user_b_id = _get_user_id(client, headers_b)
    record_id = _create_completed_record(db_session, user_b_id)

    assert (
        client.get(f"/api/resumes/{record_id}", headers=headers_a).status_code == 404
    )
    assert (
        client.get(
            f"/api/resumes/{record_id}/status", headers=headers_a
        ).status_code
        == 404
    )


# ---------- 历史对比 ----------


def test_compare_keeps_input_order(client, db_session, auth_headers):
    user_id = _get_user_id(client, auth_headers)
    id1 = _create_completed_record(db_session, user_id, overall=70)
    id2 = _create_completed_record(db_session, user_id, overall=85)

    resp = client.get(
        f"/api/resumes/compare?ids={id1},{id2}", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [item["id"] for item in body] == [id1, id2]  # 顺序与传入一致
    assert body[0]["overall_score"] == 70


def test_compare_rejects_unfinished(client, db_session, auth_headers):
    user_id = _get_user_id(client, auth_headers)
    done_id = _create_completed_record(db_session, user_id)

    pending = ResumeAnalysis(
        user_id=user_id,
        filename="pending.docx",
        stored_filename="pending.docx",
        file_ext=".docx",
        content_text="尚未分析",
    )
    db_session.add(pending)
    db_session.commit()
    db_session.refresh(pending)

    resp = client.get(
        f"/api/resumes/compare?ids={done_id},{pending.id}", headers=auth_headers
    )
    assert resp.status_code == 400


def test_compare_bad_params(client, auth_headers):
    resp = client.get("/api/resumes/compare?ids=1", headers=auth_headers)
    assert resp.status_code == 400
    resp = client.get("/api/resumes/compare?ids=abc,def", headers=auth_headers)
    assert resp.status_code == 400


# ---------- 删除（软删除） ----------


def test_delete_own_record(client, db_session, auth_headers):
    """删除自己的记录：200，行还在但 deleted_at 已写入（软删除）。"""
    user_id = _get_user_id(client, auth_headers)
    record_id = _create_completed_record(db_session, user_id)

    resp = client.delete(f"/api/resumes/{record_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "删除成功"

    row = db_session.get(ResumeAnalysis, record_id)
    assert row is not None      # 行仍在库中（软删除，非物理删除）
    assert row.deleted_at is not None


def test_deleted_record_disappears_everywhere(client, db_session, auth_headers):
    """已删记录在列表、详情、状态、对比里全部不可见。"""
    user_id = _get_user_id(client, auth_headers)
    id1 = _create_completed_record(db_session, user_id)
    id2 = _create_completed_record(db_session, user_id)

    client.delete(f"/api/resumes/{id1}", headers=auth_headers)

    assert id1 not in [r["id"] for r in client.get("/api/resumes", headers=auth_headers).json()]
    assert client.get(f"/api/resumes/{id1}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/resumes/{id1}/status", headers=auth_headers).status_code == 404
    # 对比里混入已删记录 → 整体当作"记录不存在"
    assert (
        client.get(f"/api/resumes/compare?ids={id1},{id2}", headers=auth_headers).status_code
        == 404
    )


def test_delete_twice_returns_404(client, db_session, auth_headers):
    user_id = _get_user_id(client, auth_headers)
    record_id = _create_completed_record(db_session, user_id)

    assert client.delete(f"/api/resumes/{record_id}", headers=auth_headers).status_code == 200
    assert client.delete(f"/api/resumes/{record_id}", headers=auth_headers).status_code == 404


def test_delete_processing_conflict(client, db_session, auth_headers):
    """分析中禁止删除（409）：避免与 Celery Worker 写回产生竞态。"""
    user_id = _get_user_id(client, auth_headers)
    record = ResumeAnalysis(
        user_id=user_id,
        filename="running.docx",
        stored_filename="running.docx",
        file_ext=".docx",
        content_text="分析中",
        status=STATUS_PROCESSING,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    assert client.delete(f"/api/resumes/{record.id}", headers=auth_headers).status_code == 409


def test_delete_cross_user_isolation(client, db_session, make_user):
    """越权删除：A 删不掉 B 的记录，B 的记录毫发无损。"""
    headers_a = make_user()
    headers_b = make_user()
    user_b_id = _get_user_id(client, headers_b)
    record_id = _create_completed_record(db_session, user_b_id)

    assert client.delete(f"/api/resumes/{record_id}", headers=headers_a).status_code == 404

    row = db_session.get(ResumeAnalysis, record_id)
    assert row.deleted_at is None


def test_delete_requires_auth(client):
    assert client.delete("/api/resumes/1").status_code == 401