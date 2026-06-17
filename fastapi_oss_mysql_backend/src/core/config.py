"""全局配置（基于 pydantic-settings）。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ============= 应用基础 =============
    APP_NAME: str = "fastapi-oss-mysql-backend"
    APP_ENV: Literal["dev", "test", "staging", "prod"] = "dev"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_WORKERS: int = 1
    APP_TIMEZONE: str = "Asia/Shanghai"
    API_V1_PREFIX: str = "/api/v1"

    # ============= 安全 =============
    SECRET_KEY: str = "please-change-me-in-production-32bytes-hex"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ============= MySQL =============
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "fastapi_demo"
    DB_CHARSET: str = "utf8mb4"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    # ============= Redis =============
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 20

    # ============= 阿里云 OSS =============
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
    OSS_BUCKET_NAME: str = ""
    OSS_CDN_DOMAIN: str = ""
    OSS_EXPIRE_SECONDS: int = 3600
    OSS_MAX_FILE_SIZE_MB: int = 100
    OSS_TEMP_DIR: str = "./temp"

    # ============= 日志 =============
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_ROTATION: str = "100 MB"
    LOG_RETENTION: str = "30 days"
    LOG_DIR: str = "./logs"

    # ============= 限流 =============
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # ============= CORS =============
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "*"
    CORS_HEADERS: str = "*"

    # ============= 监控 =============
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = True
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # ============= 派生属性 =============

    @property
    def DATABASE_URL(self) -> str:
        """异步数据库 URL。"""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """同步数据库 URL（用于 Alembic）。"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset={self.DB_CHARSET}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Redis URL。"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """CORS 来源列表。"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def CORS_METHODS_LIST(self) -> list[str]:
        """CORS 方法列表。"""
        return [m.strip() for m in self.CORS_METHODS.split(",") if m.strip()]

    @property
    def CORS_HEADERS_LIST(self) -> list[str]:
        """CORS 请求头列表。"""
        return [h.strip() for h in self.CORS_HEADERS.split(",") if h.strip()]

    @property
    def IS_PRODUCTION(self) -> bool:
        """是否生产环境。"""
        return self.APP_ENV == "prod"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """生产环境强制要求 SECRET_KEY 安全。"""
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度必须 >= 32 字节")
        return v


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（缓存避免重复读取）。"""
    return Settings()


# 全局配置实例
settings = get_settings()


def ensure_directories() -> None:
    """确保必要目录存在。"""
    for dir_path in (settings.LOG_DIR, settings.OSS_TEMP_DIR):
        Path(dir_path).mkdir(parents=True, exist_ok=True)
