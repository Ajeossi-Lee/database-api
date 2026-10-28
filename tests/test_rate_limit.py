"""配置开关控制 slowapi 是否生效。"""

from app.core.exceptions import register_exception_handlers
from app.middlewares.request import configure_rate_limiting
from app.settings.config import settings
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    configure_rate_limiting(app)
    return TestClient(app)


def test_rate_limit_disabled_allows_repeat_calls(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT", "1/minute")
    client = _client()
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200


def test_rate_limit_enabled_returns_unified_429(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT", "1/minute")
    client = _client()
    assert client.get("/ping").status_code == 200
    limited = client.get("/ping")
    assert limited.status_code == 429
    body = limited.json()
    assert body["code"] == 429
    assert body["message"]
    assert body["request_id"]
    assert body["details"] is None
