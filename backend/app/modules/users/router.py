from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.auth.policy import AuthMode, policy
from app.auth.security import login, refresh_tokens, revoke_session
from app.core.exceptions import UnauthorizedException
from app.modules.users.deps import get_user_service
from app.modules.users.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    LogoutRequest,
    RefreshRequest,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.modules.users.service import UserService

# 前缀由 api/v1/router.py 的 include_router(..., prefix="/users") 提供
router = APIRouter(tags=["users"])


async def _read_authenticated_user(request: Request, service: UserService):
    """从路由策略写入的当前用户读取数据库记录。"""
    auth_user = getattr(request.state, "user", None)
    if auth_user is None:
        raise UnauthorizedException("Authentication required")
    try:
        user_id = UUID(str(auth_user.id))
    except (ValueError, TypeError):
        raise UnauthorizedException("Authentication required")
    return await service.get_user(user_id)


@router.post("/register", response_model=UserRead)
async def register_endpoint(
    body: RegisterRequest,
    service: UserService = Depends(get_user_service),
):
    """注册账号。不需要登录，也不能指定角色或权限。"""
    return await service.register_user(body)


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(login_request: LoginRequest):
    """Login endpoint."""
    user = await login(login_request.username, login_request.password)
    if not user:
        raise UnauthorizedException("Incorrect username or password")
    return user


@router.post("/refresh", response_model=LoginResponse)
async def refresh_endpoint(body: RefreshRequest):
    """用刷新令牌换取新的访问令牌和刷新令牌。"""
    return await refresh_tokens(body.refresh_token)


@router.post("/logout", dependencies=[Depends(policy(auth=AuthMode.REQUIRED))])
async def logout_endpoint(request: Request, body: LogoutRequest | None = None):
    """让当前访问令牌失效。请求体里的刷新令牌会一并失效。"""
    refresh_token = body.refresh_token if body else None
    await revoke_session(getattr(request.state, "token_jti", None), refresh_token)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED))])
async def get_current_user(
    request: Request,
    service: UserService = Depends(get_user_service),
):
    """Get current user."""
    return await _read_authenticated_user(request, service)


@router.get("/profile", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED))])
async def get_profile(
    request: Request,
    service: UserService = Depends(get_user_service),
):
    """Get user profile."""
    return await _read_authenticated_user(request, service)


@router.get("", response_model=list[UserRead], dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:read"]))])
async def list_users(
    service: UserService = Depends(get_user_service),
):
    """List users."""
    return await service.list_users()


@router.post("", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service),
):
    """Create a new user."""
    return await service.create_user(user)


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:read"]))])
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    """Get a user by ID."""
    return await service.get_user(user_id)


@router.put("/{user_id}", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def update_user(
    user_id: UUID,
    user: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    """Update a user."""
    return await service.update_user(user_id, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    """Delete a user."""
    await service.delete_user(user_id)
    return {"message": "User deleted successfully"}
