"""数据库连接管理（SQLAlchemy 2.0）。

三个核心角色：
- engine：连接池，整个应用只有一个（重量级对象，不要到处 new）
- SessionLocal：会话工厂，每个请求开一个会话，用完即关
- Base：所有 ORM 模型的基类，Alembic 靠它收集全部表结构
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping：每次取连接前先 ping 一下，防止 MySQL 8 小时空闲后断连
    pool_pre_ping=True,
    # pool_recycle：连接最大复用时间，进一步规避 MySQL wait_timeout 断连问题
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有模型的公共基类。新模型务必 import 这里的 Base。"""


def get_db():
    """FastAPI 依赖：给每个请求分配一个数据库会话，请求结束自动关闭。

    路由里这样用：
        def xxx(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
