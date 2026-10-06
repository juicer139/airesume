"""安全工具：密码哈希 + JWT 签发/解析。

- 密码：bcrypt 单向哈希（自带随机盐），数据库里永远没有明文密码
- JWT：三段式 token（header.payload.signature），签名保证内容不可篡改，
  服务端无状态，不需要存 session —— 这就是选 JWT 的原因
"""
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# bcrypt 上下文：deprecated="auto" 表示将来换哈希算法时自动兼容旧哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """注册时把明文密码转成 bcrypt 哈希。"""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """登录时校验明文密码与库中哈希是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """签发 JWT。subject 一般放用户 ID（字符串形式）。

    payload 里的 exp（过期时间）是 JWT 标准字段，PyJWT 会自动校验。
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """解析 JWT，返回 subject（用户 ID）。

    token 过期 / 签名不对 / 格式错误 都返回 None，由调用方统一抛 401。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
