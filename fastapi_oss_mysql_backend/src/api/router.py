"""路由聚合：所有 v1 路由。"""
from __future__ import annotations

from fastapi import APIRouter

from src.api.v1 import auth, file, health, user

# v1 总路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(health.router, prefix="/health", tags=["健康检查"])
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/users", tags=["用户管理"])
api_router.include_router(file.router, prefix="/files", tags=["文件管理"])
