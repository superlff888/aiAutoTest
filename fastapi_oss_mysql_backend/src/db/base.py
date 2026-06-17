"""ORM 基础模型。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, BigInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """默认表名：类名转 snake_case 复数。"""
        name = cls.__name__
        # UserModel -> user_models
        import re

        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower() + "s"


class TimestampMixin:
    """时间戳混入：created_at / updated_at。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )


class IdMixin:
    """主键混入：自增 BIGINT。"""

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="主键 ID",
    )


class SoftDeleteMixin:
    """软删除混入。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        index=True,
        comment="删除时间（软删除）",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
