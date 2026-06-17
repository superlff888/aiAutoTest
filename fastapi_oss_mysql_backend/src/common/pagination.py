"""分页参数。"""
from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页查询参数。"""

    page: int = Field(default=1, ge=1, le=10_000, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页数量，最大 200")

    @property
    def offset(self) -> int:
        """计算 OFFSET。"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """计算 LIMIT。"""
        return self.page_size


def pagination_params(
    page: int = Query(1, ge=1, le=10_000, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
) -> PaginationParams:
    """FastAPI 依赖注入：分页参数。"""
    return PaginationParams(page=page, page_size=page_size)


class PageResult(BaseModel, Generic[T]):  # noqa: F821
    """分页结果（仅类型提示用）。"""

    items: list = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0
