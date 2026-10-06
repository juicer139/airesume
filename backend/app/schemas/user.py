"""用户模块的请求/响应模型（Pydantic v2）。

schema 与 model 分离的原因：
- schema 面向 API（决定收什么、吐什么），model 面向数据库（决定存什么）
- UserOut 里没有 password 字段，从根源杜绝密码泄露到响应里
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """注册请求体。Field 校验不通过时 FastAPI 自动返回 422，不用手写 if。"""

    username: str = Field(min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(description="邮箱")
    password: str = Field(min_length=6, max_length=128, description="密码")


class UserLogin(BaseModel):
    """登录请求体。"""

    username: str
    password: str


class UserOut(BaseModel):
    """返回给前端的用户信息，永远不包含密码字段。"""

    # from_attributes：允许直接从 ORM 对象转换（Pydantic v1 时代叫 orm_mode）
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    """登录成功后返回的 JWT。"""

    access_token: str
    token_type: str = "bearer"
