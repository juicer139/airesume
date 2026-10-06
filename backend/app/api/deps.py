"""公共依赖：数据库会话、当前登录用户。

FastAPI 依赖注入是本项目的粘合剂：
路由函数参数里写 Depends(xxx)，框架自动帮你执行并注入结果。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# 声明 Bearer 认证方式，Swagger 页面右上角会出现 Authorize 按钮
bearer_scheme = HTTPBearer(auto_error=False)

# 统一的 401 响应，避免每个分支重复构造
_unauthorized = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "未登录或 token 已失效",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析出当前登录用户。

    以后任何需要登录才能访问的接口，加一个参数即可：
        def xxx(current_user: User = Depends(get_current_user)):
    """
    if credentials is None:
        raise _unauthorized

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _unauthorized

    user = db.get(User, int(user_id))
    if user is None:
        raise _unauthorized
    return user
