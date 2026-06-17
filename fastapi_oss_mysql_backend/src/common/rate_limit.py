"""限流配置（slowapi）。"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.config import settings

# 全局限流器（按 IP 限流）
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri="memory://",  # 生产建议用 Redis：settings.REDIS_URL
    strategy="fixed-window",
)


def rate_limit(limit_value: str) -> callable:
    """自定义限流装饰器。

    用法：
        @router.get("/heavy")
        @rate_limit("10/minute")
        async def heavy_endpoint():
            ...
    """
    return limiter.limit(limit_value)
