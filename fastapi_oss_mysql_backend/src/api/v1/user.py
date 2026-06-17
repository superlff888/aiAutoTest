"""用户管理接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from src.common.dependencies import CurrentUser, DBSession, SuperUser
from src.common.pagination import pagination_params
from src.common.response import page_response, success
from src.core.exceptions import ErrorCode
from src.schemas.user_schema import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from src.services.user_service import UserService

router = APIRouter()


@router.post("", response_model=None, status_code=status.HTTP_201_CREATED, summary="创建用户")
async def create_user(data: UserCreateRequest, db: DBSession, _: SuperUser) -> dict:
    """创建新用户（仅超级管理员）。"""
    service = UserService(db)
    user = await service.create_user(data)
    return success(data=UserResponse.model_validate(user).model_dump(), message="创建成功")


@router.get("/me", response_model=None, summary="获取当前用户信息")
async def get_me(user: CurrentUser) -> dict:
    """获取当前登录用户的信息。"""
    return success(data=UserResponse.model_validate(user).model_dump())


@router.get("", response_model=None, summary="分页查询用户")
async def list_users(
    db: DBSession,
    _: SuperUser,
    pagination: dict = pagination_params(),  # type: ignore[assignment]
    keyword: str | None = Query(None, description="搜索关键字（用户名/邮箱）"),
    is_active: bool | None = Query(None, description="是否激活"),
) -> dict:
    """分页查询用户列表。"""
    service = UserService(db)
    users, total = await service.list_users(
        keyword=keyword,
        is_active=is_active,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return page_response(
        items=[UserResponse.model_validate(u).model_dump() for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{user_id}", response_model=None, summary="获取用户详情")
async def get_user(user_id: int, db: DBSession, _: SuperUser) -> dict:
    """根据 ID 获取用户。"""
    service = UserService(db)
    user = await service.get_user(user_id)
    return success(data=UserResponse.model_validate(user).model_dump())


@router.put("/{user_id}", response_model=None, summary="更新用户")
async def update_user(
    user_id: int, data: UserUpdateRequest, db: DBSession, _: SuperUser
) -> dict:
    """更新用户信息。"""
    service = UserService(db)
    user = await service.update_user(user_id, data)
    return success(data=UserResponse.model_validate(user).model_dump(), message="更新成功")


@router.delete("/{user_id}", response_model=None, summary="删除用户")
async def delete_user(user_id: int, db: DBSession, current: SuperUser) -> dict:
    """删除用户（软删除）。"""
    if user_id == current.id:
        from src.core.exceptions import BusinessException

        raise BusinessException(
            code=ErrorCode.CONFLICT, message="不能删除自己"
        )
    service = UserService(db)
    await service.delete_user(user_id)
    return success(message="删除成功")
