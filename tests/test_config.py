"""环境文件切换。"""

import pytest

from app.core.config import Settings, resolve_app_env, resolve_env_files


def test_resolve_env_files_by_name():
    assert resolve_env_files("staging") == (
        ".env",
        ".env.staging",
        ".env.local",
        ".env.staging.local",
    )


def test_invalid_app_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="APP_ENV"):
        resolve_app_env()


@pytest.mark.parametrize(
    ("filename", "app_env", "debug"),
    [
        (".env.dev", "dev", True),
        (".env.test", "test", False),
        (".env.staging", "staging", False),
        (".env.prod", "prod", False),
    ],
)
def test_env_file_sets_environment(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    app_env: str,
    debug: bool,
):
    """进程环境变量会盖过文件，这里去掉 APP_ENV 才能看到文件内容。"""
    monkeypatch.delenv("APP_ENV", raising=False)
    loaded = Settings(_env_file=filename)
    assert loaded.APP_ENV == app_env
    assert loaded.DEBUG is debug
