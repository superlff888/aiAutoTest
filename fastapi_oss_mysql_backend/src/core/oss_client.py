"""阿里云 OSS 客户端封装。

支持：上传、下载、删除、获取签名 URL、生成预签名上传 URL。
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import oss2

from src.core.config import settings
from src.core.exceptions import BusinessException
from src.core.logging import logger


class OSSClient:
    """OSS 客户端（单例）。"""

    def __init__(self) -> None:
        self._auth: oss2.Auth | None = None
        self._bucket: oss2.Bucket | None = None
        self._enabled: bool = False

    async def init(self) -> None:
        """初始化 OSS 客户端。"""
        # 检查配置
        if not all([
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET,
            settings.OSS_BUCKET_NAME,
        ]):
            logger.warning("⚠️  OSS 配置不完整，文件上传功能不可用")
            self._enabled = False
            return

        try:
            self._auth = oss2.Auth(
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET,
            )
            self._bucket = oss2.Bucket(
                self._auth,
                settings.OSS_ENDPOINT,
                settings.OSS_BUCKET_NAME,
            )
            # 测试连接（设置短超时）
            self._bucket.get_bucket_info()
            self._enabled = True
            logger.info(
                f"✅ OSS 初始化成功: {settings.OSS_BUCKET_NAME}@{settings.OSS_ENDPOINT}"
            )
        except oss2.exceptions.OssError as e:
            logger.error(f"❌ OSS 初始化失败: {e}")
            self._enabled = False
        except Exception as e:
            logger.error(f"❌ OSS 初始化异常: {e}")
            self._enabled = False

    async def close(self) -> None:
        """关闭客户端（OSS SDK 无显式 close）。"""
        self._bucket = None
        self._auth = None

    @property
    def is_enabled(self) -> bool:
        """OSS 是否可用。"""
        return self._enabled

    def _check_enabled(self) -> None:
        """内部检查：OSS 是否可用。"""
        if not self._enabled or self._bucket is None:
            raise BusinessException(
                code=5001,
                message="OSS 服务未启用，请检查配置",
            )

    # ============= 上传 =============

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        prefix: str = "uploads",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """上传文件到 OSS。

        Args:
            file_bytes: 文件二进制内容
            filename: 原始文件名
            prefix: 存储前缀（目录）
            content_type: MIME 类型

        Returns:
            包含 oss_key / url / size / etag 的字典
        """
        self._check_enabled()
        assert self._bucket is not None

        # 校验文件大小
        size_mb = len(file_bytes) / 1024 / 1024
        if size_mb > settings.OSS_MAX_FILE_SIZE_MB:
            raise BusinessException(
                code=5002,
                message=f"文件大小超过限制（{settings.OSS_MAX_FILE_SIZE_MB}MB）",
            )

        # 生成 OSS Key
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        oss_key = f"{prefix}/{date_prefix}/{unique_name}"

        # 头信息
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type

        # 异步上传（在线程池中执行阻塞 IO）
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._bucket.put_object(oss_key, file_bytes, headers=headers),
        )

        logger.info(f"✅ OSS 上传成功: {oss_key} ({size_mb:.2f}MB)")

        return {
            "oss_key": oss_key,
            "url": self.get_public_url(oss_key),
            "size": len(file_bytes),
            "etag": result.etag,
        }

    async def upload_local_file(
        self,
        local_path: str | Path,
        filename: str,
        *,
        prefix: str = "uploads",
    ) -> dict[str, Any]:
        """上传本地文件到 OSS。"""
        local_path = Path(local_path)
        if not local_path.exists():
            raise BusinessException(code=5003, message=f"本地文件不存在: {local_path}")

        async with aiofiles.open(local_path, "rb") as f:
            content = await f.read()
        return await self.upload_file(content, filename, prefix=prefix)

    # ============= 下载 =============

    async def download_file(self, oss_key: str) -> bytes:
        """下载 OSS 文件为字节流。"""
        self._check_enabled()
        assert self._bucket is not None

        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._bucket.get_object(oss_key)
        )
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: result.read()
        )

    async def download_to_local(self, oss_key: str, local_path: str | Path) -> None:
        """下载 OSS 文件到本地。"""
        content = await self.download_file(oss_key)
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(content)
        logger.info(f"✅ OSS 下载成功: {oss_key} -> {local_path}")

    # ============= 删除 =============

    async def delete_file(self, oss_key: str) -> None:
        """删除 OSS 文件。"""
        self._check_enabled()
        assert self._bucket is not None

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._bucket.delete_object(oss_key)
        )
        logger.info(f"✅ OSS 删除成功: {oss_key}")

    async def delete_files(self, oss_keys: list[str]) -> None:
        """批量删除 OSS 文件。"""
        self._check_enabled()
        assert self._bucket is not None

        if not oss_keys:
            return

        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._bucket.batch_delete_objects(oss_keys)
        )
        logger.info(f"✅ OSS 批量删除成功: {len(oss_keys)} 个文件")

    # ============= URL 生成 =============

    def get_public_url(self, oss_key: str) -> str:
        """获取文件公开访问 URL（需 bucket 设置公共读权限）。"""
        if settings.OSS_CDN_DOMAIN:
            return f"https://{settings.OSS_CDN_DOMAIN}/{oss_key}"
        return f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{oss_key}"

    def get_signed_url(self, oss_key: str, expires: int | None = None) -> str:
        """获取签名 URL（私有文件临时访问）。"""
        self._check_enabled()
        assert self._bucket is not None
        expire = expires or settings.OSS_EXPIRE_SECONDS
        return self._bucket.sign_url("GET", oss_key, expire)

    def get_upload_signature(self, oss_key: str, expires: int | None = None) -> dict[str, Any]:
        """生成客户端直传 OSS 的签名（前端直传用）。"""
        self._check_enabled()
        assert self._bucket is not None
        expire = expires or settings.OSS_EXPIRE_SECONDS

        # 生成 POST 策略
        import base64
        import json

        now = datetime.utcnow()
        import datetime as dt

        policy = {
            "expiration": (now + dt.timedelta(seconds=expire)).strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "conditions": [
                {"bucket": settings.OSS_BUCKET_NAME},
                ["eq", "$key", oss_key],
                ["content-length-range", 0, settings.OSS_MAX_FILE_SIZE_MB * 1024 * 1024],
            ],
        }
        policy_encode = base64.b64encode(json.dumps(policy).encode()).decode()
        signature = self._auth.bucket_sign_post  # type: ignore[union-attr]
        signed = signature(settings.OSS_BUCKET_NAME, policy_encode)

        return {
            "oss_key": oss_key,
            "url": f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}",
            "policy": policy_encode,
            "signature": signed,
            "access_key_id": settings.OSS_ACCESS_KEY_ID,
            "expire": expire,
        }


# ============= 全局实例 =============
oss_client = OSSClient()
