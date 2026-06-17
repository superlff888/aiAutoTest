"""CRUD 基类：通用 CRUD 操作。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """通用 CRUD 基类。"""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> ModelType | None:
        """根据 ID 获取。"""
        return await db.get(self.model, id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 20,
        **filters: Any,
    ) -> list[ModelType]:
        """批量获取。"""
        stmt = select(self.model).filter_by(**filters).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, **filters: Any) -> int:
        """统计数量。"""
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def create(self, db: AsyncSession, **data: Any) -> ModelType:
        """创建记录。"""
        obj = self.model(**data)
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update(
        self, db: AsyncSession, id: int, **data: Any
    ) -> ModelType | None:
        """根据 ID 更新。"""
        obj = await self.get(db, id)
        if obj is None:
            return None
        for key, value in data.items():
            if value is not None:  # 只更新非 None 字段
                setattr(obj, key, value)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, id: int) -> bool:
        """根据 ID 删除（物理删除）。"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.rowcount > 0
