"""框架一致性：统一错误体、分页边界、探针不泄露数据库错误。"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from slowapi.errors import RateLimitExceeded

from app.core.exceptions import UnauthorizedException, register_exception_handlers
from app.db.session import get_db
from app.middlewares.request import RequestIDMiddleware, _rate_limit_handler
from app.modules.genes.deps import get_page_params
from app.modules.health.router import router as health_router
from app.modules.users import router as users_router_module
from app.modules.users.router import router as users_router


class _BrokenSession:
    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("secret-db-detail")

    async def rollback(self):
        return None


def _clear_rate_limit() -> None:
    from app.middlewares import request as request_module

    request_module.limiter.limiter.storage.reset()


def test_page_below_one_is_rejected():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/page")
    async def read_page(page_params=Depends(get_page_params)):
        return {"page": page_params.page, "page_size": page_params.page_size}

    client = TestClient(app)
    assert client.get("/page", params={"page": 0}).status_code == 422
    assert client.get("/page", params={"page_size": 101}).status_code == 422
    ok = client.get("/page")
    assert ok.status_code == 200
    assert ok.json() == {"page": 1, "page_size": 20}


def test_readiness_hides_database_error():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(health_router)

    async def broken_db():
        yield _BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    client = TestClient(app)
    ready = client.get("/readyz")
    assert ready.status_code == 503
    assert ready.json()["status"] == "unready"
    assert "secret-db-detail" not in ready.text
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/v1/healthz").status_code == 404


def test_request_id_reaches_log_context():
    from app.core.logging import request_id_var

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    seen: dict[str, str] = {}

    @app.get("/ping")
    async def ping():
        seen["id"] = request_id_var.get()
        return {"ok": True}

    client = TestClient(app)
    accepted = client.get("/ping", headers={"X-Request-ID": "req-ctx"})
    assert accepted.headers["X-Request-ID"] == "req-ctx"
    assert seen["id"] == "req-ctx"
    rejected = client.get("/ping", headers={"X-Request-ID": "bad id"})
    assert rejected.headers["X-Request-ID"] != "bad id"
    assert seen["id"] == rejected.headers["X-Request-ID"]


def test_login_failure_uses_error_envelope(monkeypatch):
    async def fail_login(_username, _password):
        raise UnauthorizedException("Incorrect username or password")

    monkeypatch.setattr(users_router_module, "login", fail_login)
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(users_router, prefix="/api/v1/users")
    _clear_rate_limit()
    response = TestClient(app).post(
        "/api/v1/users/login",
        json={"username": "ada", "password": "correct-password"},
        headers={"X-Request-ID": "req-login"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert body["request_id"] == "req-login"
    assert "correct-password" not in response.text
    _clear_rate_limit()


def test_login_route_rate_limit(monkeypatch):
    async def fail_login(_username, _password):
        raise UnauthorizedException("Incorrect username or password")

    monkeypatch.setattr(users_router_module, "login", fail_login)
    app = FastAPI()
    register_exception_handlers(app)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.include_router(users_router, prefix="/api/v1/users")
    _clear_rate_limit()
    client = TestClient(app)
    payload = {"username": "ada", "password": "correct-password"}
    for _ in range(20):
        assert client.post("/api/v1/users/login", json=payload).status_code == 401
    blocked = client.post("/api/v1/users/login", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["code"] == 429
    _clear_rate_limit()
