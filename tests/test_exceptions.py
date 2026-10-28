"""统一错误响应。"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.exceptions import NotFoundException, register_exception_handlers
from app.middlewares.request import RequestIDMiddleware
from app.settings.config import settings


class _Item(BaseModel):
    name: str


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/missing")
    async def missing():
        raise NotFoundException("Gene not found")

    @app.get("/http")
    async def http_error():
        raise HTTPException(status_code=400, detail="File validation failed")

    @app.post("/items")
    async def create_item(item: _Item):
        return item

    @app.get("/boom")
    async def boom():
        raise RuntimeError("database password leaked")

    return TestClient(app, raise_server_exceptions=False)


def test_app_exception_uses_request_id_and_details():
    response = _client().get("/missing", headers={"X-Request-ID": "req-app"})
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 404
    assert body["message"] == "Gene not found"
    assert body["request_id"] == "req-app"
    assert body["details"] is None
    assert response.headers["X-Request-ID"] == "req-app"
    assert "error" not in body


def test_http_exception_uses_same_shape():
    response = _client().get("/http", headers={"X-Request-ID": "req-http"})
    assert response.status_code == 400
    body = response.json()
    assert body == {
        "code": 400,
        "message": "File validation failed",
        "request_id": "req-http",
        "details": None,
    }


def test_validation_error_puts_fields_in_details():
    response = _client().post("/items", json={}, headers={"X-Request-ID": "req-valid"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["message"] == "Validation error"
    assert body["request_id"] == "req-valid"
    assert body["details"][0]["loc"] == ["body", "name"]
    assert body["details"][0]["message"]


def test_unexpected_error_hides_internal_message(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", False)
    response = _client().get("/boom", headers={"X-Request-ID": "req-boom"})
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == 500
    assert body["message"] == "Internal server error"
    assert body["request_id"] == "req-boom"
    assert body["details"] is None
    assert "database password" not in response.text
    assert "error" not in body
