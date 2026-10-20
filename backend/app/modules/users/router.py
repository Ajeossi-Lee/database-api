from fastapi import APIRouter, Depends, status
from app.modules.users.deps import get_user_service
from app.modules.users.service import UserService
from app.modules.users.schemas import UserCreate, UserUpdate, UserRead, LoginRequest, LoginResponse
from app.db.session import get_db
from app.core.security import CurrentUser, OptionalUser, login
from app.core.exceptions import UnauthorizedException
from app.core.auth_policy import AuthMode, policy
from typing import Optional


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(login_request: LoginRequest):
    """Login endpoint."""
    user = await login(login_request.username, login_request.password)
    if not user:
        raise UnauthorizedException("Incorrect username or password")
    return user


@router.get("/me", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED))])
async def get_current_user(current_user: OptionalUser = Depends()):
    """Get current user."""
    if not current_user:
        raise UnauthorizedException("Authentication required")
    return current_user


@router.get("/profile", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED))])
async def get_profile(current_user: CurrentUser = Depends()):
    """Get user profile."""
    return current_user


@router.get("/users/{user_id}", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:read"]))])
async def get_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
):
    """Get a user by ID."""
    return await service.get_user(user_id)


@router.get("/users", response_model=list[UserRead], dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:read"]))])
async def list_users(
    service: UserService = Depends(get_user_service),
):
    """List users."""
    return await service.list_users()


@router.post("/users", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def create_user(
    user: UserCreate,
    service: UserService = Depends(get_user_service),
):
    """Create a new user."""
    return await service.create_user(user)


@router.put("/users/{user_id}", response_model=UserRead, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def update_user(
    user_id: str,
    user: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    """Update a user."""
    return await service.update_user(user_id, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["user:manage"]))])
async def delete_user(
    user_id: str,
    service: UserService = Depends(get_user_service),
):
    """Delete a user."""
    await service.delete_user(user_id)
    return {"message": "User deleted successfully"}