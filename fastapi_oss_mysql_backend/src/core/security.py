"""安全模块：JWT、密码加密、Token 工具。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.exceptions import BusinessException

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============= 密码 =============

def hash_password(plain: str) -> str:
    """密码加密。"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希是否匹配。"""
    return pwd_context.verify(plain, hashed)


# ============= JWT =============

def create_access_token(
    subject: str | int,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """创建访问 Token。"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(tz=timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "iat": datetime.now(tz=timezone.utc),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | int,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """创建刷新 Token。"""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.now(tz=timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """解码并验证 Token。

    Raises:
        BusinessException: Token 无效或过期
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        raise BusinessException(
            code=4001,
            message=f"Token 无效: {e}",
        ) from e


def get_subject_from_token(token: str) -> str:
    """从 Token 中提取 subject（用户 ID）。"""
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise BusinessException(code=4001, message="Token 缺少 subject")
    return str(sub)


# ============= 初始化 =============

def init_security() -> None:
    """安全模块初始化检查。"""
    if settings.IS_PRODUCTION and "change-me" in settings.SECRET_KEY:
        raise RuntimeError(
            "🚨 生产环境必须修改 SECRET_KEY！"
            "生成方法: openssl rand -hex 32"
        )
