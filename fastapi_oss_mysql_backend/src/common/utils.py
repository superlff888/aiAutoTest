"""通用工具函数。"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.exceptions import ValidationException


# ============= 时间 =============

def utc_now() -> datetime:
    """获取当前 UTC 时间（无时区）。"""
    return datetime.utcnow()


def format_datetime(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间。"""
    return dt.strftime(fmt) if dt else ""


# ============= 文件 =============

def safe_filename(filename: str) -> str:
    """清理文件名，移除危险字符。"""
    # 移除路径分隔符
    filename = filename.replace("/", "_").replace("\\", "_")
    # 移除控制字符
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    # 限制长度
    name = Path(filename).name
    if len(name) > 200:
        stem, suffix = Path(name).stem, Path(name).suffix
        name = stem[: 200 - len(suffix)] + suffix
    return name


def calculate_file_hash(content: bytes, algorithm: str = "md5") -> str:
    """计算文件哈希。"""
    h = hashlib.new(algorithm)
    h.update(content)
    return h.hexdigest()


def humanize_size(size_bytes: int) -> str:
    """人类可读的文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ("KB", "MB", "GB", "TB"):
        size_bytes /= 1024
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
    return f"{size_bytes:.2f} PB"


# ============= 字符串 =============

def mask_email(email: str) -> str:
    """邮箱脱敏：a***@example.com。"""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****1234。"""
    if len(phone) != 11:
        return phone
    return phone[:3] + "****" + phone[7:]


# ============= 校验 =============

def validate_password_strength(password: str) -> None:
    """校验密码强度：8+ 字符，包含大小写字母+数字。"""
    if len(password) < 8:
        raise ValidationException("密码长度不能少于 8 位")
    if not re.search(r"[A-Z]", password):
        raise ValidationException("密码必须包含大写字母")
    if not re.search(r"[a-z]", password):
        raise ValidationException("密码必须包含小写字母")
    if not re.search(r"\d", password):
        raise ValidationException("密码必须包含数字")


# ============= 字典 =============

def remove_none(data: dict[str, Any]) -> dict[str, Any]:
    """递归移除字典中的 None 值。"""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if v is None:
            continue
        if isinstance(v, dict):
            result[k] = remove_none(v)
        else:
            result[k] = v
    return result
