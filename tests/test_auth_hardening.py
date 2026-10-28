"""认证、权限通配、令牌类型和用户路径。"""

from uuid import UUID

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router
from app.auth.policy import AuthMode, policy
from app.auth.security import (
    User,
    _revoked_jtis,
    authenticate_user,
    check_permissions,
    create_access_token,
    create_refresh_token,
    get_user_by_id,
    hash_password_util,
    refresh_tokens,
    revoke_jti,
)
from app.core.exceptions import ForbiddenException, UnauthorizedException, register_exception_handlers
from app.main import app as application
from app.settings.config import settings


USER_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(autouse=True)
def _clear_revoked_tokens():
    _revoked_jtis.clear()
    yield
    _revoked_jtis.clear()


class _Row:
    def __init__(self, *, active: bool = True, password: str = "correct-password"):
        self.id = USER_ID
        self.username = "ada"
        self.email = "ada@example.com"
        self.is_active = active
        self.is_superuser = False
        self.permissions = ["gene:read"]
        self.roles = ["viewer"]
        self.hashed_password = hash_password_util(password)


class _Session:
    def __init__(self, row):
        self.row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def scalar(self, _statement):
        return self.row


def _patch_session(monkeypatch, row):
    monkeypatch.setattr(
        "app.auth.security.AsyncSessionFactory",
        lambda: _Session(row),
    )


def _policy_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get(
        "/write",
        dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["gene:write"]))],
    )
    async def write():
        return {"ok": True}

    return app


async def _as_user(user_id: str) -> User:
    return User(
        id=user_id,
        username="curator",
        email="curator@example.com",
        is_active=True,
        permissions=["gene:*"],
        roles=["curator"],
    )


@pytest.mark.asyncio
async def test_wildcard_permission_covers_resource_action():
    curator = User(
        id="1",
        username="curator",
        permissions=["gene:*"],
        roles=["curator"],
    )
    await check_permissions(curator, ["gene:write"], [], "all")
    with pytest.raises(ForbiddenException):
        await check_permissions(curator, ["user:manage"], [], "all")

    admin = User(id="2", username="admin", permissions=["*:*"], roles=[])
    await check_permissions(admin, ["user:manage", "gene:delete"], [], "all")

    viewer = User(id="3", username="viewer", permissions=["gene:read"], roles=["viewer"])
    await check_permissions(viewer, ["gene:read"], [], "all")
    with pytest.raises(ForbiddenException):
        await check_permissions(viewer, ["gene:write"], [], "all")
    await check_permissions(viewer, ["gene:write", "gene:read"], [], "any")

    root = User(id="4", username="root", permissions=[], roles=[], is_superuser=True)
    await check_permissions(root, ["gene:delete"], ["missing-role"], "all")


@pytest.mark.asyncio
async def test_refresh_token_cannot_call_protected_route(monkeypatch):
    user = await _as_user(str(USER_ID))

    async def fake_get_user(user_id: str):
        if user_id == str(USER_ID):
            return user
        return None

    monkeypatch.setattr("app.auth.security.get_user_by_id", fake_get_user)
    access = await create_access_token({"sub": str(USER_ID)})
    refresh = await create_refresh_token({"sub": str(USER_ID)})
    client = TestClient(_policy_app())

    allowed = client.get("/write", headers={"Authorization": f"Bearer {access}"})
    assert allowed.status_code == 200

    rejected = client.get("/write", headers={"Authorization": f"Bearer {refresh}"})
    assert rejected.status_code == 401


@pytest.mark.asyncio
async def test_revoked_access_token_is_rejected(monkeypatch):
    user = await _as_user(str(USER_ID))

    async def fake_get_user(user_id: str):
        return user if user_id == str(USER_ID) else None

    monkeypatch.setattr("app.auth.security.get_user_by_id", fake_get_user)
    access = await create_access_token({"sub": str(USER_ID)})
    payload = jwt.decode(
        access,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )
    revoke_jti(payload["jti"])
    client = TestClient(_policy_app())
    response = client.get("/write", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_and_rejects_access_token(monkeypatch):
    user = await _as_user(str(USER_ID))

    async def fake_get_user(user_id: str):
        return user if user_id == str(USER_ID) else None

    monkeypatch.setattr("app.auth.security.get_user_by_id", fake_get_user)
    access = await create_access_token({"sub": str(USER_ID)})
    refresh = await create_refresh_token({"sub": str(USER_ID)})

    with pytest.raises(UnauthorizedException):
        await refresh_tokens(access)

    first = await refresh_tokens(refresh)
    assert first.access_token
    assert first.refresh_token != refresh
    with pytest.raises(UnauthorizedException):
        await refresh_tokens(refresh)


@pytest.mark.asyncio
async def test_authenticate_user_checks_password(monkeypatch):
    _patch_session(monkeypatch, _Row())
    matched = await authenticate_user("ada", "correct-password")
    assert matched is not None
    assert matched.username == "ada"
    assert await authenticate_user("ada", "wrong-password") is None

    _patch_session(monkeypatch, None)
    assert await authenticate_user("admin", "anything") is None


@pytest.mark.asyncio
async def test_inactive_user_cannot_authenticate(monkeypatch):
    _patch_session(monkeypatch, _Row(active=False))
    assert await authenticate_user("ada", "correct-password") is None


@pytest.mark.asyncio
async def test_get_user_by_id_does_not_use_mock_accounts(monkeypatch):
    def _boom():
        raise AssertionError("非 UUID 不应查询数据库")

    monkeypatch.setattr("app.auth.security.AsyncSessionFactory", _boom)
    assert await get_user_by_id("admin-id") is None
    assert await get_user_by_id("curator-id") is None


def _included_paths() -> list[str]:
    """拼出 include_router 之后的完整路径。"""
    paths: list[str] = []
    for included in api_router.routes:
        prefix = included.include_context.prefix.rstrip("/")
        for route in included.original_router.routes:
            path = getattr(route, "path", "") or ""
            if path in ("", "/"):
                paths.append(prefix)
            else:
                paths.append(prefix + path)
    return paths


def test_user_routes_have_single_prefix():
    paths = _included_paths()
    assert "/api/v1/users/register" in paths
    assert "/api/v1/users/login" in paths
    assert "/api/v1/users/refresh" in paths
    assert "/api/v1/users/logout" in paths
    assert "/api/v1/users/me" in paths
    assert "/api/v1/users/{user_id}" in paths
    assert "/api/v1/users" in paths
    assert all("/users/users" not in path for path in paths)


def test_sql_regex_and_auth_middleware_are_not_registered():
    names = [middleware.cls.__name__ for middleware in application.user_middleware]
    assert "SQLInjectionProtectionMiddleware" not in names
    assert "EnforceAuthMiddleware" not in names
    assert "SecurityHeadersMiddleware" in names
