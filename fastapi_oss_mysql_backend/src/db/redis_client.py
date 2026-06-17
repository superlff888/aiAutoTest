"""Redis 客户端。"""
from __future__ import annotations

import redis.asyncio as aioredis

from src.core.config import settings
from src.core.logging import logger

# 全局 Redis 客户端
_redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """初始化 Redis 连接池。"""
    global _redis_client
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    try:
        await _redis_client.ping()
        logger.info(f"✅ Redis 连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        _redis_client = None


async def close_redis() -> None:
    """关闭 Redis 连接池。"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("✅ Redis 连接池已关闭")


def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端。"""
    if _redis_client is None:
        raise RuntimeError("Redis 未初始化")
    return _redis_client
