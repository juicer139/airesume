"""简历分析记录表。

这张表是整个平台的核心业务表，生命周期贯穿阶段 4~8：
- 阶段 4：上传时写入（status=pending），保存提取出的纯文本
- 阶段 6：Celery 任务执行时更新 status
- 阶段 7：AI 结果写入 result_json
- 阶段 8：历史对比就是查询这张表的多条记录
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 状态机：pending(已上传待分析) → processing(任务执行中) → completed / failed
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# 上传限制：扩展名白名单 + 大小上限
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class ResumeAnalysis(Base):
    """一条简历分析记录 = 一次上传。"""

    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 外键 + 级联删除：用户注销时其记录一并删除
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # ---- 文件信息 ----
    filename: Mapped[str] = mapped_column(String(255))         # 用户上传时的原始文件名
    stored_filename: Mapped[str] = mapped_column(String(255))  # 磁盘上的 uuid 文件名（防重名/路径攻击）
    file_ext: Mapped[str] = mapped_column(String(10))

    # ---- 内容 ----
    content_text: Mapped[str] = mapped_column(Text)      # 解析出的纯文本，AI 只消费它
    job_description: Mapped[str | None] = mapped_column(Text)  # 目标岗位 JD（可选，阶段 7 用于匹配打分）

    # ---- 任务状态 ----
    status: Mapped[str] = mapped_column(
        String(20), default=STATUS_PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)    # failed 时的原因
    result_json: Mapped[dict | None] = mapped_column(JSON)     # AI 结构化分析结果（阶段 7）

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
        # ---- 软删除 ----
    # NULL = 正常记录；非 NULL = 用户已删除（列表/详情/对比一律过滤掉）。
    # 软删除不真删行、不删磁盘文件，为将来"恢复"和审计留余地。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
