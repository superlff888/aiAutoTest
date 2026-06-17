"""用户表。"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.file import FileRecord


class User(Base, IdMixin, TimestampMixin):
    """用户表。"""

    __tablename__ = "users"

    # ============= 基础信息 =============
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True, comment="邮箱"
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="姓名"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True, comment="手机号"
    )
    avatar: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="头像 URL"
    )

    # ============= 鉴权信息 =============
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希（bcrypt）"
    )

    # ============= 状态 =============
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True, comment="是否激活"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否超级管理员"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最后登录时间"
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="最后登录 IP"
    )

    # ============= 关联 =============
    files: Mapped[list["FileRecord"]] = relationship(
        "FileRecord",
        back_populates="uploader",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
