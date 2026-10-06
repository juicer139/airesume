"""用户模块路由：注册 / 登录 / 获取当前用户。

分层原则：路由层只做"收参数 → 调逻辑 → 返回结果"，
复杂业务以后放 services 层，这里保持薄。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """注册新用户。用户名或邮箱已被占用时返回 409。"""
    exists = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名或邮箱已被注册")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()          # 提交事务，数据真正落库
    db.refresh(user)     # 刷新拿到数据库生成的 id / created_at
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """登录：校验密码后签发 JWT，前端保存，之后每次请求放进 Authorization 头。"""
    user = db.query(User).filter(User.username == payload.username).first()
    # "用户不存在"和"密码错误"返回同一句提示，防止攻击者撞库探测用户名
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户。前端启动时用它验证本地 token 是否仍有效。"""
    return current_user
