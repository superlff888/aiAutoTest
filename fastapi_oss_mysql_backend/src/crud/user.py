"""用户 CRUD。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.db.models.user import User


class UserCRUD(CRUDBase[User]):
    """用户 CRUD。"""

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """根据用户名查询。"""
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """根据邮箱查询。"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(
        self, db: AsyncSession, identifier: str
    ) -> User | None:
        """根据用户名或邮箱查询（登录用）。"""
        stmt = select(User).where(
            or_(User.username == identifier, User.email == identifier)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(
        self,
        db: AsyncSession,
        *,
        keyword: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """分页查询用户。"""
        conditions: list[Any] = []
        if keyword:
            conditions.append(
                or_(
                    User.username.like(f"%{keyword}%"),
                    User.email.like(f"%{keyword}%"),
                    User.full_name.like(f"%{keyword}%"),
                )
            )
        if is_active is not None:
            conditions.append(User.is_active == is_active)

        # 列表
        stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        users = list(result.scalars().all())

        # 总数
        count_stmt = select(User).where(*conditions)
        count = len((await db.execute(count_stmt)).scalars().all())

        return users, count

    async def update_last_login(
        self, db: AsyncSession, user_id: int, ip: str | None = None
    ) -> None:
        """更新最后登录时间。"""
        from datetime import datetime

        user = await self.get(db, user_id)
        if user is None:
            return
        user.last_login_at = datetime.utcnow()
        if ip:
            user.last_login_ip = ip


# 单例
user_crud = UserCRUD(User)
