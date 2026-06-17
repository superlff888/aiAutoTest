"""测试全局夹具。

策略：
- 使用测试数据库（DB_NAME=test_db）
- 每个测试函数前清空数据
- OSS 用 mock 替代
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.security import hash_password
from src.db.base import Base
from src.db.models.user import User

# ============= 事件循环 =============


@pytest.fixture(scope="session")
def event_loop():
    """会话级事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============= 异步引擎 =============


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """测试数据库引擎（每个 session 创建一次）。"""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    # 启动时建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """每个测试函数独立的 session。"""
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_maker() as session:
        # 每个测试清空数据
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        yield session
        await session.rollback()


# ============= 依赖覆盖 =============


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 测试客户端。"""

    # 覆盖 get_db
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        session_maker = async_sessionmaker(
            bind=test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        async with session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Mock OSS 客户端
    with patch("src.core.oss_client.oss_client") as mock_oss:
        mock_oss.is_enabled = True
        mock_oss.init = AsyncMock()
        mock_oss.close = AsyncMock()
        mock_oss.upload_file = AsyncMock(
            return_value={
                "oss_key": "test/2024/01/01/abc.png",
                "url": "https://test-bucket.oss-cn-hangzhou.aliyuncs.com/test/2024/01/01/abc.png",
                "size": 1024,
                "etag": "test-etag",
            }
        )
        mock_oss.delete_file = AsyncMock()
        mock_oss.get_signed_url = AsyncMock(return_value="https://signed-url")

        # 延迟导入以保证 mock 生效
        from src.api.v1 import file  # noqa: F401
        from src.common import dependencies  # noqa: F401
        from src.main import app

        app.dependency_overrides[dependencies.get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

        app.dependency_overrides.clear()


# ============= 辅助 fixtures =============


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """普通用户。"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("Test1234"),
        full_name="测试用户",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """超级管理员。"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("Admin1234"),
        full_name="系统管理员",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    """生成带 token 的请求头。"""
    from src.core.security import create_access_token

    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}
