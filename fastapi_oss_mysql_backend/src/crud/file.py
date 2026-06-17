"""文件 CRUD。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.db.models.file import FileRecord


class FileCRUD(CRUDBase[FileRecord]):
    """文件 CRUD。"""

    async def get_by_oss_key(self, db: AsyncSession, oss_key: str) -> FileRecord | None:
        """根据 OSS Key 查询。"""
        stmt = select(FileRecord).where(FileRecord.oss_key == oss_key)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, db: AsyncSession, file_hash: str
    ) -> FileRecord | None:
        """根据文件哈希查询（去重用）。"""
        stmt = select(FileRecord).where(FileRecord.file_hash == file_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_files(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        business_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[FileRecord], int]:
        """查询某用户的文件列表。"""
        conditions: list[Any] = [
            FileRecord.uploader_id == user_id,
            FileRecord.is_deleted == False,  # noqa: E712
        ]
        if business_type:
            conditions.append(FileRecord.business_type == business_type)

        # 列表
        stmt = (
            select(FileRecord)
            .where(*conditions)
            .order_by(FileRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        # 总数
        from sqlalchemy import func

        count_stmt = (
            select(func.count())
            .select_from(FileRecord)
            .where(*conditions)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        return items, int(total)

    async def soft_delete(self, db: AsyncSession, file_id: int) -> bool:
        """软删除文件。"""
        record = await self.get(db, file_id)
        if record is None:
            return False
        record.is_deleted = True
        await db.flush()
        return True


# 单例
file_crud = FileCRUD(FileRecord)
