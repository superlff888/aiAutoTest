"""文件相关 Schema。"""
from __future__ import annotations

from pydantic import Field

from src.schemas.common import BaseSchema, TimestampSchema


class FileInfoResponse(BaseSchema, TimestampSchema):
    """文件信息响应。"""

    id: int = Field(..., description="文件 ID")
    original_filename: str = Field(..., description="原始文件名")
    oss_key: str = Field(..., description="OSS 存储 Key")
    file_size: int = Field(..., description="文件大小（字节）")
    content_type: str | None = Field(default=None, description="MIME 类型")
    file_ext: str | None = Field(default=None, description="扩展名")
    url: str | None = Field(default=None, description="访问 URL")
    signed_url: str | None = Field(default=None, description="签名 URL（私有文件）")
    bucket_name: str = Field(..., description="Bucket 名称")
    storage_prefix: str = Field(..., description="存储前缀")
    uploader_id: int = Field(..., description="上传者 ID")
    business_type: str | None = Field(default=None, description="业务类型")
    business_id: int | None = Field(default=None, description="业务 ID")
