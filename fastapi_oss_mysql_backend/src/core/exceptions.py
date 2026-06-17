"""全局统一异常。"""
from __future__ import annotations

from typing import Any


class BusinessException(Exception):
    """业务异常基类。

    用法：
        raise BusinessException(code=1001, message="用户不存在")
        raise BusinessException(code=4001, message="无权限", http_code=403)
    """

    def __init__(
        self,
        *,
        code: int = 1000,
        message: str = "业务异常",
        http_code: int = 400,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_code = http_code
        self.data = data
        super().__init__(message)


# ============= 业务异常码定义 =============

class NotFoundException(BusinessException):
    """资源未找到（404）。"""

    def __init__(self, message: str = "资源不存在", data: Any = None) -> None:
        super().__init__(code=404, message=message, http_code=404, data=data)


class AuthException(BusinessException):
    """认证失败（401）。"""

    def __init__(self, message: str = "认证失败", data: Any = None) -> None:
        super().__init__(code=401, message=message, http_code=401, data=data)


class PermissionException(BusinessException):
    """权限不足（403）。"""

    def __init__(self, message: str = "无权限", data: Any = None) -> None:
        super().__init__(code=403, message=message, http_code=403, data=data)


class ValidationException(BusinessException):
    """参数校验失败（422）。"""

    def __init__(self, message: str = "参数错误", data: Any = None) -> None:
        super().__init__(code=422, message=message, http_code=422, data=data)


class ConflictException(BusinessException):
    """资源冲突（409）。"""

    def __init__(self, message: str = "资源冲突", data: Any = None) -> None:
        super().__init__(code=409, message=message, http_code=409, data=data)


class RateLimitException(BusinessException):
    """限流（429）。"""

    def __init__(self, message: str = "请求过于频繁", data: Any = None) -> None:
        super().__init__(code=429, message=message, http_code=429, data=data)


# ============= 错误码常量 =============

class ErrorCode:
    """错误码常量。"""

    # 通用 (1xxx)
    SUCCESS = 0
    UNKNOWN = 1000
    PARAM_ERROR = 1001
    NOT_FOUND = 1002
    CONFLICT = 1003

    # 认证 (2xxx)
    AUTH_FAILED = 2001
    TOKEN_EXPIRED = 2002
    TOKEN_INVALID = 2003
    PERMISSION_DENIED = 2004

    # 用户 (3xxx)
    USER_NOT_FOUND = 3001
    USER_EXISTS = 3002
    PASSWORD_ERROR = 3003

    # 文件 (4xxx)
    FILE_NOT_FOUND = 4001
    FILE_TOO_LARGE = 4002
    FILE_TYPE_ERROR = 4003
    UPLOAD_FAILED = 4004

    # OSS (5xxx)
    OSS_DISABLED = 5001
    OSS_FILE_TOO_LARGE = 5002
    OSS_FILE_NOT_FOUND = 5003
    OSS_UPLOAD_ERROR = 5004
