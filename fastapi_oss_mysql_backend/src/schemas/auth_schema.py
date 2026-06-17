"""认证相关 Schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求。"""

    refresh_token: str = Field(..., description="Refresh Token")


class TokenResponse(BaseModel):
    """Token 响应。"""

    access_token: str = Field(..., description="访问 Token")
    refresh_token: str = Field(..., description="刷新 Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="Access Token 过期时间（秒）")
