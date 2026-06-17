"""认证业务逻辑。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import AuthException, ErrorCode
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from src.crud.user import user_crud
from src.db.models.user import User
from src.schemas.auth_schema import TokenResponse


class AuthService:
    """认证服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(
        self, *, username: str, password: str, ip: str | None = None
    ) -> TokenResponse:
        """用户登录。"""
        # 1. 查询用户
        user = await user_crud.get_by_username_or_email(self.db, username)
        if user is None:
            raise AuthException("用户名或密码错误")

        # 2. 校验状态
        if not user.is_active:
            raise AuthException("用户已禁用")

        # 3. 校验密码
        if not verify_password(password, user.hashed_password):
            raise AuthException("用户名或密码错误")

        # 4. 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        if ip:
            user.last_login_ip = ip
        await self.db.flush()

        # 5. 生成 Token
        return self._build_token_response(user)

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """刷新 Access Token。"""
        # 1. 解码 refresh token
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise AuthException("Token 类型错误，需要 refresh token")

        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise AuthException("Token 缺少用户信息")

        try:
            user_id = int(user_id_raw)
        except (ValueError, TypeError) as e:
            raise AuthException("Token 用户 ID 无效") from e

        # 2. 查询用户
        user = await user_crud.get(self.db, user_id)
        if user is None or not user.is_active:
            raise AuthException("用户不存在或已禁用")

        # 3. 生成新 Token
        return self._build_token_response(user)

    def _build_token_response(self, user: User) -> TokenResponse:
        """构造 Token 响应。"""
        extra_claims = {
            "username": user.username,
            "is_superuser": user.is_superuser,
        }
        access_token = create_access_token(user.id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
