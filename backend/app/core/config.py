"""应用配置。用 APP_ENV 切换四套环境文件。"""

import os
from typing import Literal, cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["dev", "test", "staging", "prod"]
_APP_ENVS: tuple[AppEnv, ...] = ("dev", "test", "staging", "prod")


def resolve_app_env() -> AppEnv:
    """读取 APP_ENV，未设置时默认为 dev。非法值在启动时失败。"""
    raw = os.getenv("APP_ENV", "dev").strip().lower()
    if raw not in _APP_ENVS:
        allowed = " / ".join(_APP_ENVS)
        raise ValueError(f"APP_ENV 必须是 {allowed} 之一，当前为 {raw!r}")
    return cast(AppEnv, raw)


def resolve_env_files(app_env: AppEnv | None = None) -> tuple[str, ...]:
    """返回要加载的环境文件。后面的文件覆盖前面的文件。"""
    name = resolve_app_env() if app_env is None else app_env
    return (
        ".env",
        f".env.{name}",
        ".env.local",
        f".env.{name}.local",
    )


class Settings(BaseSettings):
    # 当前环境，由 APP_ENV 或对应的 .env.<环境> 决定
    APP_ENV: AppEnv = "dev"

    # Application
    PROJECT_NAME: str = "Database API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = Field(...)
    DB_POOL_SIZE: int = Field(20, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(30, description="数据库连接池最大溢出数量")
    DB_POOL_RECYCLE: int = Field(3600, description="连接回收时间（秒）")
    DB_POOL_PRE_PING: bool = Field(True, description="连接前检查连接有效性")

    # Slow query log
    LOG_MIN_DURATION_STATEMENT: int = Field(1000, description="慢查询阈值（毫秒）")

    # Security
    SECRET_KEY: str = Field(...)
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_ISSUER: str = "database-api"
    JWT_AUDIENCE: str = "database-api-users"

    # Authentication
    AUTH_ENABLED: bool = Field(True)
    AUTH_DEFAULT_MODE: Literal["public", "optional", "required"] = "required"
    AUTH_POLICY_FILE: str = "config/auth_policy.yaml"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)

    # Logging
    LOG_LEVEL: str = "INFO"

    # Performance
    WORKER_COUNT: int = Field(4, description="工作进程数")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=resolve_env_files(),
        env_file_encoding="utf-8",
    )


# 导入时即加载配置，缺必填项会在启动阶段失败
settings = Settings()