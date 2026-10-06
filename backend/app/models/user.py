"""用户表模型（SQLAlchemy 2.0 声明式写法）。

Mapped[int] + mapped_column 是 2.0 的新写法：类型注解直接声明数据库类型，
比旧版 Column 更直观，IDE 补全也更友好。
"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """用户表：注册/登录的主体，也是所有简历分析记录的归属者。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # unique=True + index=True：既防止重复注册，又加速"按用户名查用户"（登录高频操作）
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # 只存 bcrypt 哈希，永远不存明文密码
    hashed_password: Mapped[str] = mapped_column(String(255))
    # server_default=func.now()：由 MySQL 生成创建时间，不依赖 Python 进程时钟
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
