"""FastAPI 项目入口

启动方式：
    开发：uv run uvicorn src.main:app --reload
    生产：uv run python src/main.py
"""
from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# 将项目根目录加入 path，便于直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from src.api.router import api_router  # noqa: E402
from src.common.middleware import (  # noqa: E402
    ProcessTimeMiddleware,
    RequestIDMiddleware,
)
from src.core.config import settings  # noqa: E402
from src.core.database import close_db, init_db  # noqa: E402
from src.core.exceptions import BusinessException  # noqa: E402
from src.core.logging import logger  # noqa: E402
from src.core.oss_client import oss_client  # noqa: E402
from src.core.security import init_security  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动 → 业务 → 关闭。"""
    # ========== 启动 ==========
    logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION} (env={settings.APP_ENV})")
    logger.info(f"📚 API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")

    try:
        # 初始化数据库连接池
        await init_db()
        logger.info("✅ 数据库连接池初始化完成")

        # 初始化 OSS 客户端
        await oss_client.init()
        logger.info("✅ OSS 客户端初始化完成")

        # 初始化安全模块（生成默认密钥等）
        init_security()
        logger.info("✅ 安全模块初始化完成")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        raise

    yield  # 应用运行中

    # ========== 关闭 ==========
    logger.info("🛑 关闭服务 ...")
    try:
        await close_db()
        await oss_client.close()
        logger.info("✅ 资源清理完成")
    except Exception as e:
        logger.error(f"❌ 关闭时出错: {e}")


def create_app() -> FastAPI:
    """工厂函数：创建 FastAPI 实例。"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="FastAPI + MySQL + OSS 后端工程模板",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ========== CORS 跨域 ==========
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS_LIST,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS_LIST,
        allow_headers=settings.CORS_HEADERS_LIST,
    )

    # ========== 自定义中间件 ==========
    app.add_middleware(RequestIDMiddleware)  # 请求 ID
    app.add_middleware(ProcessTimeMiddleware)  # 请求耗时

    # ========== 全局异常处理 ==========
    @app.exception_handler(BusinessException)
    async def business_exception_handler(request, exc: BusinessException) -> JSONResponse:
        """业务异常。"""
        logger.warning(f"业务异常: {exc.message} (code={exc.code})")
        return JSONResponse(
            status_code=exc.http_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": exc.data,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc: StarletteHTTPException) -> JSONResponse:
        """HTTP 异常。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "data": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request, exc: RequestValidationError
    ) -> JSONResponse:
        """参数校验异常。"""
        logger.warning(f"参数校验失败: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "参数校验失败",
                "data": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception) -> JSONResponse:
        """兜底异常。"""
        logger.exception(f"未捕获异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误" if not settings.APP_DEBUG else str(exc),
                "data": None,
            },
        )

    # ========== 路由注册 ==========
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ========== Prometheus 监控 ==========
    if settings.PROMETHEUS_ENABLED:
        Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


# ============= 应用实例 =============
app = create_app()


def run() -> None:
    """程序化启动入口（用于 pyproject.toml 的 [project.scripts]）。"""
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.APP_DEBUG,
    )


if __name__ == "__main__":
    run()
