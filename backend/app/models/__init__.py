# models 包：SQLAlchemy 数据库模型
# 在这里统一导入所有模型，Alembic 才能"看到"全部表结构
from app.models.resume_analysis import ResumeAnalysis  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["ResumeAnalysis", "User"]
