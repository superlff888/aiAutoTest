"""日志配置（loguru）。"""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.core.config import settings


def setup_logging() -> None:
    """初始化日志。"""
    # 移除默认 handler
    logger.remove()

    # 控制台 handler（带颜色）
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=settings.APP_DEBUG,
        enqueue=True,  # 异步安全
    )

    # 文件 handler（生产环境）
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "app.log",
        level=settings.LOG_LEVEL,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        ),
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        enqueue=True,
    )

    # 错误日志单独输出
    logger.add(
        log_dir / "error.log",
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}\n{exception}"
        ),
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # 拦截标准库 logging
    import logging

    logging.basicConfig(handlers=[logging.NullHandler()], level=0, force=True)

    # 拦截 uvicorn / sqlalchemy / asyncio 等日志
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).handlers = [InterceptHandler()]


class InterceptHandler(logging.Handler):
    """将标准库 logging 重定向到 loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# 初始化（main.py 中导入时即生效）
setup_logging()
