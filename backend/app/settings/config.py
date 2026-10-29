"""
应用配置的加载入口。

环境文件放在仓库根目录的 envs/.env.<环境>。
本文件只按 APP_ENV 读取对应的那一个文件。
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["dev", "test", "staging", "prod"]
_APP_ENVS: tuple[AppEnv, ...] = ("dev", "test", "staging", "prod")


# 读取 envs 目录
ENV_DIR = Path(__file__).resolve().parents[3] / "envs"


def resolve_env_file() -> str:
    """按 APP_ENV 返回 envs/.env.<环境>。未设置时为 dev，非法值在启动时失败。"""
    raw = os.getenv("APP_ENV", "dev").strip().lower()
    if raw not in _APP_ENVS:
        allowed = " / ".join(_APP_ENVS)
        raise ValueError(f"APP_ENV 必须是 {allowed} 之一，当前为 {raw!r}")
    return str(ENV_DIR / f".env.{raw}")


class Settings(BaseSettings):
    # 当前环境，由 APP_ENV 或对应的 .env.<环境> 决定
    APP_ENV: AppEnv = "dev"

    # Application
    PROJECT_NAME: str = "Database API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database。异步引擎要求驱动写成 postgresql+asyncpg://
    DATABASE_URL: str = Field(...)

    DB_POOL_SIZE: int = Field(20, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(30, description="数据库连接池最大溢出数量")
    DB_POOL_RECYCLE: int = Field(3600, description="连接回收时间（秒）")
    DB_POOL_PRE_PING: bool = Field(True, description="连接前检查连接有效性")

    # Slow query log
    LOG_MIN_DURATION_STATEMENT: int = Field(1000, description="慢查询阈值（毫秒）")

    # Security
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_ISSUER: str = "database-api"
    JWT_AUDIENCE: str = "database-api-users"

    # Authentication
    AUTH_ENABLED: bool = Field(True)
    AUTH_DEFAULT_MODE: Literal["public", "optional", "required"] = "required"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)
    # Host 头校验。testserver 供测试客户端使用
    ALLOWED_HOSTS: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    # 限流。关闭时不拦截请求
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT: str = Field("1000/minute", description="单个来源地址的请求频率上限")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=resolve_env_file(),
        env_file_encoding="utf-8",
    )


# 导入时即加载配置，缺必填项会在启动阶段失败
settings = Settings()
