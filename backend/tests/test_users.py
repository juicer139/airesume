"""用户模块测试：注册 / 登录 / JWT 保护。"""
import uuid


def _register_payload() -> dict:
    username = f"u{uuid.uuid4().hex[:8]}"
    return {
        "username": username,
        "email": f"{username}@test.com",
        "password": "secret123",
    }


def test_register_success(client):
    resp = client.post("/api/users/register", json=_register_payload())
    assert resp.status_code == 201
    body = resp.json()
    # 响应里永远不能出现密码相关字段
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_rejected(client):
    payload = _register_payload()
    assert client.post("/api/users/register", json=payload).status_code == 201
    assert client.post("/api/users/register", json=payload).status_code == 409


def test_register_invalid_payload(client):
    """用户名过短 / 邮箱格式错 / 密码过短 → Pydantic 校验 422。"""
    resp = client.post(
        "/api/users/register",
        json={"username": "ab", "email": "not-an-email", "password": "123"},
    )
    assert resp.status_code == 422


def test_login_and_me_roundtrip(client):
    payload = _register_payload()
    client.post("/api/users/register", json=payload)

    resp = client.post(
        "/api/users/login",
        json={"username": payload["username"], "password": payload["password"]},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == payload["username"]


def test_login_wrong_password(client):
    payload = _register_payload()
    client.post("/api/users/register", json=payload)

    resp = client.post(
        "/api/users/login",
        json={"username": payload["username"], "password": "wrong-password"},
    )
    # 统一提示，不暴露"用户存在但密码错"
    assert resp.status_code == 401


def test_me_without_token(client):
    assert client.get("/api/users/me").status_code == 401


def test_me_with_garbage_token(client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/users/me", headers=headers).status_code == 401
