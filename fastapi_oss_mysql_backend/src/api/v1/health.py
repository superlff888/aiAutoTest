"""健康检查接口。"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from sqlalchemy import text

from src.common.response import success
from src.core.config import settings
from src.core.database import get_session_maker
from src.core.logging import logger
from src.core.oss_client import oss_client
from src.db.redis_client import get_redis

router = APIRouter()

# 启动时间
_START_TIME = time.time()


@router.get("/live", summary="存活探针")
async def liveness() -> dict:
    """K8s liveness 探针。"""
    return success({"status": "alive", "version": settings.APP_VERSION})


@router.get("/ready", summary="就绪探针")
async def readiness() -> dict:
    """K8s readiness 探针：检查依赖是否可用。"""
    checks: dict[str, dict] = {"app": {"status": "ok"}}
    overall_ok = True

    # 检查数据库
    try:
        start = time.perf_counter()
        async with get_session_maker()() as session:
            await session.execute(text("SELECT 1"))
        checks["mysql"] = {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception as e:
        checks["mysql"] = {"status": "error", "message": str(e)}
        overall_ok = False

    # 检查 Redis
    try:
        start = time.perf_counter()
        redis = get_redis()
        await redis.ping()
        checks["redis"] = {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    except Exception as e:
        checks["redis"] = {"status": "error", "message": str(e)}
        overall_ok = False
    except RuntimeError:
        checks["redis"] = {"status": "skipped", "message": "Redis 未启用"}

    # 检查 OSS
    if oss_client.is_enabled:
        checks["oss"] = {"status": "ok"}
    else:
        checks["oss"] = {"status": "skipped", "message": "OSS 未启用"}

    checks["app"]["uptime_seconds"] = round(time.time() - _START_TIME, 2)

    return success(
        data={"healthy": overall_ok, "checks": checks},
        message="ok" if overall_ok else "degraded",
    )
