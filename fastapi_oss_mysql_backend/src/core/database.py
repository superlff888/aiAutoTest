"""MySQL 数据库连接（异步 SQLAlchemy 2.0）。"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.logging import logger
from src.db.base import Base

# ============= 全局引擎 =============
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """初始化数据库引擎与连接池。"""
    global _engine, _session_maker
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,  # 自动检测断连
        future=True,
    )
    _session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # 健康检查
    try:
        async with _engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info(f"✅ 数据库连接成功: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise


async def close_db() -> None:
    """关闭数据库连接池。"""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("✅ 数据库连接池已关闭")


def get_engine() -> AsyncEngine:
    """获取数据库引擎（供 Alembic 等使用）。"""
    if _engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """获取 session 工厂。"""
    if _session_maker is None:
        raise RuntimeError("数据库未初始化，请先调用 init_db()")
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取数据库 Session。

    用法：
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _session_maker is None:
        raise RuntimeError("数据库未初始化")

    async with _session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """开发用：直接根据 ORM 创建所有表（生产请用 Alembic）。"""
    if _engine is None:
        await init_db()
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ 数据表已创建")
