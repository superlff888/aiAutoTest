"""认证接口：登录、刷新 Token。"""
from __future__ import annotations

from fastapi import APIRouter

from src.common.dependencies import DBSession
from src.common.response import success
from src.schemas.auth_schema import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from src.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=None, summary="用户登录")
async def login(data: LoginRequest, db: DBSession) -> dict:
    """用户登录获取 Token。"""
    service = AuthService(db)
    result = await service.login(username=data.username, password=data.password)
    return success(data=result.model_dump(), message="登录成功")


@router.post("/refresh", response_model=None, summary="刷新 Token")
async def refresh_token(data: RefreshTokenRequest, db: DBSession) -> dict:
    """使用 refresh_token 刷新 access_token。"""
    service = AuthService(db)
    result = await service.refresh_access_token(data.refresh_token)
    return success(data=result.model_dump(), message="刷新成功")
