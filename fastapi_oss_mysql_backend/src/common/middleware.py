"""全局中间件：请求 ID、请求耗时、访问日志。"""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求 ID 中间件。"""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        # 优先使用上游传入的 Request-ID
        request_id = request.headers.get(self.HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[self.HEADER] = request_id
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """请求耗时中间件。"""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 响应头
        response.headers["X-Process-Time"] = f"{elapsed_ms:.2f}ms"

        # 访问日志
        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            f"{request.method} {request.url.path} | "
            f"status={response.status_code} | "
            f"elapsed={elapsed_ms:.2f}ms | "
            f"request_id={request_id}"
        )

        return response
