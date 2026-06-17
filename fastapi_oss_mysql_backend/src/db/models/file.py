"""OSS 文件记录表。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class FileRecord(Base, IdMixin, TimestampMixin):
    """OSS 文件上传记录表。"""

    __tablename__ = "file_records"

    # ============= 文件信息 =============
    original_filename: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="原始文件名"
    )
    oss_key: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False, index=True, comment="OSS 存储 Key"
    )
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="文件 MD5/SHA256"
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="文件大小（字节）"
    )
    content_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="MIME 类型"
    )
    file_ext: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True, comment="扩展名"
    )

    # ============= 业务信息 =============
    storage_prefix: Mapped[str] = mapped_column(
        String(50), default="uploads", nullable=False, comment="存储目录前缀"
    )
    bucket_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="OSS Bucket 名称"
    )
    url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="访问 URL"
    )
    etag: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="OSS ETag"
    )

    # ============= 状态 =============
    is_deleted: Mapped[bool] = mapped_column(
        default=False, nullable=False, index=True, comment="是否软删除"
    )
    business_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="业务类型"
    )
    business_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, comment="业务 ID"
    )

    # ============= 上传者 =============
    uploader_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="上传者用户 ID",
    )
    uploader: Mapped["User"] = relationship("User", back_populates="files", lazy="joined")

    def __repr__(self) -> str:
        return f"<FileRecord(id={self.id}, key={self.oss_key})>"
