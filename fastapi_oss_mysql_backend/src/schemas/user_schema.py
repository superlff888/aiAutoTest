"""用户相关 Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from src.common.utils import validate_password_strength
from src.schemas.common import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """用户基础字段。"""

    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    email: EmailStr = Field(..., description="邮箱")
    full_name: str | None = Field(default=None, max_length=100, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")


class UserCreateRequest(UserBase):
    """创建用户请求。"""

    password: str = Field(min_length=8, max_length=128, description="密码")

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserUpdateRequest(BaseSchema):
    """更新用户请求。"""

    email: EmailStr | None = Field(default=None, description="邮箱")
    full_name: str | None = Field(default=None, max_length=100, description="姓名")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    is_active: bool | None = Field(default=None, description="是否激活")


class UserResponse(UserBase, TimestampSchema):
    """用户响应。"""

    id: int = Field(..., description="用户 ID")
    avatar: str | None = Field(default=None, description="头像 URL")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级管理员")
    last_login_at: datetime | None = Field(default=None, description="最后登录时间")
