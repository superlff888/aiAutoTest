"""初始化数据脚本

创建默认管理员、角色、字典等基础数据。
用法：uv run python scripts/init_data.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.logging import logger  # noqa: E402
from src.core.security import hash_password  # noqa: E402
from src.db.models.user import User  # noqa: E402
from src.db.session import async_session_maker  # noqa: E402


async def create_default_admin() -> None:
    """创建默认超级管理员。"""
    async with async_session_maker() as session:
        async with session.begin():
            # 检查是否已存在
            result = await session.execute(
                select(User).where(User.username == "admin")
            )
            if result.scalar_one_or_none():
                logger.info("⏭  管理员已存在，跳过创建")
                return

            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=hash_password("admin123456"),
                full_name="系统管理员",
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)
            logger.success("✅ 默认管理员创建成功 (admin / admin123456)")


async def main() -> None:
    """主函数。"""
    logger.info(f"🚀 开始初始化数据 (env={settings.APP_ENV}) ...")
    try:
        await create_default_admin()
        logger.success("🎉 初始化完成")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
