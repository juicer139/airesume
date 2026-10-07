"""pytest 全局夹具。

测试的核心原则：**不依赖任何外部服务**。
- 数据库：用 SQLite 内存库替换 MySQL（SQLAlchemy 模型是跨库的）
- Redis/Celery：测试只涉及"入队前"的接口逻辑，不触发真实任务
- AI：对比类测试直接往库里写 result_json，绕过 AI 调用

关键手法：dependency_overrides 把 get_db 换成测试会话，
路由代码零改动就能跑在测试库上。
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# StaticPool + 内存库：整个测试进程共享同一个 SQLite 连接，
# 否则"建表的连接"和"测试用的连接"不是同一个，会报表不存在
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """整个测试会话建一次表，结束销毁。"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """给测试用例直接操作数据库的会话（造数据用）。"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """带数据库覆盖的 FastAPI 测试客户端。"""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    """工厂夹具：注册并登录一个随机用户，返回带 token 的请求头。"""

    def _make() -> dict[str, str]:
        username = f"u{uuid.uuid4().hex[:8]}"
        client.post(
            "/api/users/register",
            json={
                "username": username,
                "email": f"{username}@test.com",
                "password": "secret123",
            },
        )
        resp = client.post(
            "/api/users/login",
            json={"username": username, "password": "secret123"},
        )
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _make


@pytest.fixture
def auth_headers(make_user):
    """单个已登录用户的请求头（最常用）。"""
    return make_user()
