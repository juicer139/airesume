"""Alembic 迁移环境。

相比 alembic init 生成的默认版本，改了两处：
1. 数据库连接串从 app 的 Settings 读取（.env 注入），不在本文件写密码
2. target_metadata 指向我们的 Base.metadata，`alembic revision --autogenerate`
   才能对比出模型与数据库的差异，自动生成迁移脚本
"""# 数据库连接由 alembic/env.py 从 .env 注入，backend\alembic.ini不写任何密码
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  导入以把所有模型注册进 Base.metadata
from app.core.config import get_settings
from app.core.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL 不连库（少用）。"""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接连库执行迁移（常用）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
