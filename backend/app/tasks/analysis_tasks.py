"""Celery 任务：简历 AI 分析（在 Worker 进程中执行）。

关键认知：Worker 是完全独立的进程，不共享 FastAPI 的任何内存状态，
所以不能复用请求级的 get_db 依赖，必须在任务里自己开会话并负责关闭。
"""
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.resume_analysis import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    ResumeAnalysis,
)
from app.services.ai.provider import AIProviderError, get_ai_provider

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_analysis")
def run_analysis(record_id: int) -> str:
    """执行一条分析记录的 AI 分析，结果写回 MySQL。

    状态流转：pending → processing → completed / failed
    """
    db = SessionLocal()
    try:
        record = db.get(ResumeAnalysis, record_id)
        if record is None:
            logger.warning("分析任务找不到记录 %s", record_id)
            return "record_not_found"

        record.status = STATUS_PROCESSING
        db.commit()

        try:
            result = get_ai_provider().analyze_resume(
                record.content_text, record.job_description
            )
        except AIProviderError as e:
            record.status = STATUS_FAILED
            record.error_message = str(e)
            db.commit()
            logger.error("记录 %s 分析失败：%s", record_id, e)
            return STATUS_FAILED

        record.result_json = result.model_dump()
        record.status = STATUS_COMPLETED
        record.error_message = None
        db.commit()
        return STATUS_COMPLETED
    finally:
        db.close()
