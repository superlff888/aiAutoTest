"""文件管理接口：OSS 上传、下载、删除。"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, Query, UploadFile

from src.common.dependencies import CurrentUser, DBSession
from src.common.pagination import pagination_params
from src.common.response import page_response, success
from src.core.exceptions import BusinessException, ErrorCode
from src.schemas.file_schema import FileInfoResponse
from src.services.file_service import FileService

router = APIRouter()


@router.post("/upload", response_model=None, summary="上传文件到 OSS")
async def upload_file(
    file: UploadFile = File(..., description="文件"),
    db: DBSession = ...,  # type: ignore[assignment]
    user: CurrentUser = ...,  # type: ignore[assignment]
    business_type: str | None = Form(None, description="业务类型"),
    business_id: int | None = Form(None, description="业务 ID"),
    prefix: str = Form("uploads", description="存储前缀"),
) -> dict:
    """上传文件到 OSS 并记录到数据库。"""
    if not file.filename or not file.content_type:
        raise BusinessException(code=ErrorCode.PARAM_ERROR, message="文件信息不完整")

    # 读取文件内容
    content = await file.read()
    if not content:
        raise BusinessException(code=ErrorCode.PARAM_ERROR, message="文件内容为空")

    service = FileService(db)
    record = await service.upload_file(
        user=user,
        file_content=content,
        original_filename=file.filename,
        content_type=file.content_type,
        business_type=business_type,
        business_id=business_id,
        prefix=prefix,
    )
    return success(
        data=FileInfoResponse.model_validate(record).model_dump(),
        message="上传成功",
    )


@router.get("/{file_id}", response_model=None, summary="获取文件信息")
async def get_file_info(file_id: int, db: DBSession, user: CurrentUser) -> dict:
    """获取文件详情（含签名 URL）。"""
    service = FileService(db)
    record = await service.get_file_info(file_id, current_user=user)
    return success(data=FileInfoResponse.model_validate(record).model_dump())


@router.get("", response_model=None, summary="分页查询我的文件")
async def list_my_files(
    db: DBSession,
    user: CurrentUser,
    pagination: dict = pagination_params(),  # type: ignore[assignment]
    business_type: str | None = Query(None, description="业务类型"),
) -> dict:
    """分页查询当前用户上传的文件。"""
    service = FileService(db)
    items, total = await service.list_user_files(
        user_id=user.id,
        business_type=business_type,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return page_response(
        items=[FileInfoResponse.model_validate(r).model_dump() for r in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.delete("/{file_id}", response_model=None, summary="删除文件")
async def delete_file(file_id: int, db: DBSession, user: CurrentUser) -> dict:
    """删除文件（OSS + 数据库）。"""
    service = FileService(db)
    await service.delete_file(file_id, current_user=user)
    return success(message="删除成功")
