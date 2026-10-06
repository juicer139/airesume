"""简历上传与记录路由（阶段 4）。

两个安全细节值得记住：
1. 所有查询都带 user_id 过滤——防止越权读写别人的简历（水平越权是常见漏洞）
2. 上传三重校验：扩展名白名单 → 大小限制 → 内容解析兜底
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.resume_analysis import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    STATUS_PENDING,
    STATUS_PROCESSING,
    ResumeAnalysis,
)
from app.models.user import User
from app.schemas.resume import ResumeOut
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
        .filter(ResumeAnalysis.user_id == current_user.id)
        .order_by(ResumeAnalysis.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{record_id}", response_model=ResumeOut)
def get_resume(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询单条记录。注意过滤条件同时带 id 和 user_id。"""
    record = (
        db.query(ResumeAnalysis)
        .filter(
            ResumeAnalysis.id == record_id,
            ResumeAnalysis.user_id == current_user.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")
    return record


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
