"""全局依赖注入：鉴权、获取当前用户。"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import AuthException, PermissionException
from src.core.security import decode_token
from src.crud.user import user_crud
from src.db.models.user import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization Header 解析当前用户。

    用法：
        @router.get("/me")
        async def get_me(user: User = Depends(get_current_user)):
            return user
    """
    if not authorization:
        raise AuthException("缺少 Authorization Header")

    # 支持 "Bearer xxx" 或直接 "xxx"
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
    elif len(parts) == 1:
        token = parts[0]
    else:
        raise AuthException("Authorization Header 格式错误")

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthException("Token 类型错误，需要 access token")

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise AuthException("Token 缺少用户信息")

    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError) as e:
        raise AuthException("Token 用户 ID 无效") from e

    user = await user_crud.get(db, user_id)
    if user is None:
        raise AuthException("用户不存在")

    if not user.is_active:
        raise AuthException("用户已禁用")

    return user


async def get_current_active_superuser(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """获取当前超级管理员。"""
    if not user.is_superuser:
        raise PermissionException("需要超级管理员权限")
    return user


# 常用类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]
SuperUser = Annotated[User, Depends(get_current_active_superuser)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
