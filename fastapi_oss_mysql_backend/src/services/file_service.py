"""文件业务逻辑。"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils import calculate_file_hash, safe_filename
from src.core.config import settings
from src.core.exceptions import BusinessException, ErrorCode
from src.core.oss_client import oss_client
from src.crud.file import file_crud
from src.db.models.file import FileRecord
from src.db.models.user import User


class FileService:
    """文件服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upload_file(
        self,
        *,
        user: User,
        file_content: bytes,
        original_filename: str,
        content_type: str | None = None,
        business_type: str | None = None,
        business_id: int | None = None,
        prefix: str = "uploads",
    ) -> FileRecord:
        """上传文件到 OSS。"""
        if not oss_client.is_enabled:
            raise BusinessException(
                code=ErrorCode.OSS_DISABLED, message="OSS 服务未启用"
            )

        # 1. 文件名校验
        safe_name = safe_filename(original_filename)

        # 2. 计算哈希（去重 / 防重复上传）
        file_hash = calculate_file_hash(file_content, algorithm="md5")

        # 3. 上传到 OSS
        result = await oss_client.upload_file(
            file_bytes=file_content,
            filename=safe_name,
            prefix=prefix,
            content_type=content_type,
        )

        # 4. 数据库记录
        file_ext = Path(safe_name).suffix.lstrip(".").lower() or None
        record = await file_crud.create(
            self.db,
            original_filename=safe_name,
            oss_key=result["oss_key"],
            file_hash=file_hash,
            file_size=result["size"],
            content_type=content_type,
            file_ext=file_ext,
            storage_prefix=prefix,
            bucket_name=settings.OSS_BUCKET_NAME,
            url=result["url"],
            etag=result["etag"],
            is_deleted=False,
            business_type=business_type,
            business_id=business_id,
            uploader_id=user.id,
        )
        await self.db.commit()
        return record

    async def get_file_info(self, file_id: int, *, current_user: User) -> FileRecord:
        """获取文件详情（生成签名 URL）。"""
        record = await file_crud.get(self.db, file_id)
        if record is None or record.is_deleted:
            raise BusinessException(
                code=ErrorCode.FILE_NOT_FOUND, message="文件不存在"
            )

        # 鉴权：仅上传者或超级管理员可看
        if record.uploader_id != current_user.id and not current_user.is_superuser:
            raise BusinessException(code=ErrorCode.PERMISSION_DENIED, message="无权限查看")

        # 生成签名 URL（私有 bucket 场景）
        if oss_client.is_enabled:
            try:
                record.signed_url = oss_client.get_signed_url(record.oss_key)  # type: ignore[attr-defined]
            except Exception:
                record.signed_url = None  # type: ignore[attr-defined]
        else:
            record.signed_url = None  # type: ignore[attr-defined]

        return record

    async def list_user_files(
        self,
        *,
        user_id: int,
        business_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[FileRecord], int]:
        """分页查询某用户的文件。"""
        return await file_crud.list_user_files(
            self.db,
            user_id=user_id,
            business_type=business_type,
            offset=offset,
            limit=limit,
        )

    async def delete_file(self, file_id: int, *, current_user: User) -> None:
        """删除文件（软删除 + OSS 物理删除）。"""
        record = await file_crud.get(self.db, file_id)
        if record is None or record.is_deleted:
            raise BusinessException(
                code=ErrorCode.FILE_NOT_FOUND, message="文件不存在"
            )

        # 鉴权
        if record.uploader_id != current_user.id and not current_user.is_superuser:
            raise BusinessException(code=ErrorCode.PERMISSION_DENIED, message="无权限删除")

        # 软删除数据库
        record.is_deleted = True

        # 删除 OSS 文件（失败不抛错，记录日志）
        if oss_client.is_enabled:
            try:
                await oss_client.delete_file(record.oss_key)
            except Exception as e:
                # 仅记录日志，不影响主流程（OSS 文件可后台异步清理）
                from src.core.logging import logger

                logger.warning(f"OSS 删除失败（{record.oss_key}）: {e}")

        await self.db.commit()
