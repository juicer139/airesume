"""简历上传与记录路由（阶段 4）。

两个安全细节值得记住：
1. 所有查询都带 user_id 过滤——防止越权读写别人的简历（水平越权是常见漏洞）
2. 上传三重校验：扩展名白名单 → 大小限制 → 内容解析兜底
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.resume_analysis import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    ResumeAnalysis,
)
from app.models.user import User
from app.schemas.analysis import AnalysisResult
from app.schemas.resume import CompareItem, ResumeDetail, ResumeOut
from app.services.parser import extract_text
from app.tasks.analysis_tasks import run_analysis

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])
settings = get_settings()


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传简历（multipart/form-data），解析文本后创建一条 pending 记录。

    job_description 可选，粘贴目标岗位 JD，阶段 7 用于匹配打分。
    """
    # ---- 1. 扩展名白名单 ----
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "仅支持 PDF / Word(.docx) 文件")

    # ---- 2. 大小限制（先读进内存再判断，简历场景文件都小，可接受）----
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件不能超过 10MB")

    # ---- 3. 解析兜底：提不出文本直接拒绝 ----
    try:
        text = extract_text(ext, content)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    # ---- 保存文件到磁盘（uuid 命名，防止重名覆盖和路径穿越攻击）----
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / stored_filename).write_bytes(content)

    record = ResumeAnalysis(
        user_id=current_user.id,
        filename=file.filename,
        stored_filename=stored_filename,
        file_ext=ext,
        content_text=text,
        job_description=job_description.strip() or None,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户的分析记录，最新在前（历史页数据源）。"""
    return (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
            ) 
        .order_by(ResumeAnalysis.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/compare", response_model=list[CompareItem])
def compare_resumes(
    ids: str = Query(..., description="逗号分隔的两个记录 ID，如 ?ids=3,5"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """对比两条已完成的分析记录。

    注意：本路由必须声明在 /{record_id} 之前——否则 "compare" 会被
    当作 record_id 尝试转 int，直接 422。路由声明顺序就是匹配顺序。
    """
    parts = [p.strip() for p in ids.split(",") if p.strip()]
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "请恰好提供两个记录 ID，如 ?ids=3,5"
        )
    id_list = [int(p) for p in parts]

    # in_ 一次查两条，且必须带 user_id——防止越权对比别人的记录
    records = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id.in_(id_list),
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
        ) 
        .all()
    )
    if len(records) != 2:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在或无权访问")

    items: list[CompareItem] = []
    # 按用户传入的顺序返回（第一个是基准 A，第二个是 B）
    for record in sorted(records, key=lambda r: id_list.index(r.id)):
        if record.status != STATUS_COMPLETED or not record.result_json:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"记录 {record.id} 尚未完成分析，无法对比",
            )
        result = AnalysisResult.model_validate(record.result_json)
        items.append(
            CompareItem(
                id=record.id,
                filename=record.filename,
                created_at=record.created_at,
                overall_score=result.overall_score,
                completeness=result.completeness,
                jd_match_score=result.jd_match.score if result.jd_match else None,
                strengths=result.strengths,
                weaknesses=result.weaknesses,
                suggestions=result.suggestions,
            )
        )
    return items


@router.get("/{record_id}", response_model=ResumeDetail)
def get_resume(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录详情（报告页数据源）：元信息 + AI 结果 + 解析出的简历原文。"""
    record = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == record_id,
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
        ) 
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")

    return ResumeDetail(
        id=record.id,
        filename=record.filename,
        status=record.status,
        error_message=record.error_message,
        job_description=record.job_description,
        content_text=record.content_text,
        created_at=record.created_at,
        result=(
            AnalysisResult.model_validate(record.result_json)
            if record.result_json
            else None
        ),
    )

@router.delete("/{record_id}")
def delete_resume(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除分析记录（软删除：置 deleted_at，不删行、不删磁盘文件）。

    两个刻意的设计：
    1. 已删记录再删返回 404——幂等语义清晰，也避免暴露"这条到底存不存在"
    2. processing 状态返回 409——Celery Worker 此刻正拿着这条记录跑 AI，
       让它等分析结束再删，避免任务写回与删除产生竞态
    """
    record = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == record_id,
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
        ) 
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")
    if record.status == STATUS_PROCESSING:
        raise HTTPException(status.HTTP_409_CONFLICT, "该记录正在分析中，请稍候")
    record.deleted_at = datetime.now()
    db.commit()
    return {"id": record.id, "message": "删除成功"}   



@router.post("/{record_id}/analyze")
def create_analysis_task(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建异步分析任务：入队后立即返回 task_id，前端轮询状态接口。

    对比阶段 5 的同步版本：接口响应从 10~60 秒降到毫秒级，
    Web 进程不再被 AI 调用阻塞——这就是引入 Celery 的全部意义。
    """
    record = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == record_id,
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
        ) 
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")
    if record.status == STATUS_PROCESSING:
        raise HTTPException(status.HTTP_409_CONFLICT, "该记录正在分析中，请稍候")

    # 重置状态并入队（支持失败后重新分析、完成后重新分析）
    record.status = STATUS_PENDING
    record.error_message = None
    db.commit()

    task = run_analysis.delay(record.id)  # 把任务消息推进 Redis 队列
    return {
        "record_id": record.id,
        "task_id": task.id,      # Celery 任务 ID，可用于排查日志
        "status": record.status,
    }


@router.get("/{record_id}/status")
def get_analysis_status(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """前端轮询接口：只返回轻量状态字段，不携带结果大 JSON。"""
    record = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == record_id,
            ResumeAnalysis.user_id == current_user.id,
            ResumeAnalysis.deleted_at.is_(None),
        ) 
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")

    return {
        "record_id": record.id,
        "status": record.status,
        "error_message": record.error_message,
    }
