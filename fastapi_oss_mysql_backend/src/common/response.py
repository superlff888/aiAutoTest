"""统一响应格式。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from src.core.exceptions import ErrorCode

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """统一响应结构。"""

    code: int = Field(default=ErrorCode.SUCCESS, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="业务数据")


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """成功响应。"""
    return {
        "code": ErrorCode.SUCCESS,
        "message": message,
        "data": data,
    }


def fail(
    code: int = ErrorCode.UNKNOWN,
    message: str = "fail",
    data: Any = None,
) -> dict[str, Any]:
    """失败响应。"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def page_response(
    items: list[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """分页响应。"""
    return success(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }
    )
