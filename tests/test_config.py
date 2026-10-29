"""环境文件切换。"""

import pytest

from app.settings.config import ENV_DIR, Settings, resolve_env_file


def test_resolve_env_file_by_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "staging")
    assert resolve_env_file() == str(ENV_DIR / ".env.staging")


def test_resolve_env_file_defaults_to_dev(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert resolve_env_file() == str(ENV_DIR / ".env.dev")


def test_invalid_app_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError, match="APP_ENV"):
        resolve_env_file()


@pytest.mark.parametrize(
    ("filename", "app_env", "debug"),
    [
        (str(ENV_DIR / ".env.dev"), "dev", True),
        (str(ENV_DIR / ".env.test"), "test", False),
        (str(ENV_DIR / ".env.staging"), "staging", False),
        (str(ENV_DIR / ".env.prod"), "prod", False),
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
