"""自助注册：公开、不能提升权限、用户名冲突返回 409。"""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers
from app.modules.users.deps import get_user_service
from app.modules.users.router import router as users_router
from app.modules.users.service import UserService

USER_ID = UUID("33333333-3333-3333-3333-333333333333")


class _Repo:
    def __init__(self):
        self.rows = []
        self.last_create = None

    async def get_user_by_username(self, username):
        return next((row for row in self.rows if row.username == username), None)

    async def get_user_by_email(self, email):
        if not email:
            return None
        return next((row for row in self.rows if row.email == email), None)

    async def create_user(self, user_create):
        now = datetime.now(timezone.utc)
        row = SimpleNamespace(
            id=USER_ID,
            username=user_create.username,
            email=user_create.email,
            is_active=user_create.is_active,
            is_superuser=user_create.is_superuser,
            permissions=list(user_create.permissions),
            roles=list(user_create.roles),
            created_at=now,
            updated_at=now,
        )
        self.rows.append(row)
        self.last_create = user_create
        return row


def _client(repo: _Repo) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(users_router, prefix="/api/v1/users")

    async def override_service():
        service = UserService(session=None)
        service.repository = repo
        return service

    app.dependency_overrides[get_user_service] = override_service
    return TestClient(app)


def test_register_creates_normal_user_without_auth():
    repo = _Repo()
    response = _client(repo).post(
        "/api/v1/users/register",
        json={
            "username": "ada",
            "password": "correct-password",
            "email": "ada@example.com",
            "is_superuser": True,
            "permissions": ["*:*"],
            "roles": ["admin"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    user = body["data"]
    assert user["username"] == "ada"
    assert user["email"] == "ada@example.com"
    assert user["is_superuser"] is False
    assert user["permissions"] == []
    assert user["roles"] == []
    assert "password" not in body
    assert "hashed_password" not in body
    assert repo.last_create.is_superuser is False
    assert repo.last_create.permissions == []
    assert repo.last_create.roles == []


def test_register_rejects_short_password():
    response = _client(_Repo()).post(
        "/api/v1/users/register",
        json={"username": "ada", "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 422


def test_register_conflicts_on_existing_username():
    repo = _Repo()
    client = _client(repo)
    payload = {"username": "ada", "password": "correct-password"}
    assert client.post("/api/v1/users/register", json=payload).status_code == 200
    again = client.post("/api/v1/users/register", json=payload)
    assert again.status_code == 409
    assert again.json()["message"] == "User with this username already exists"
