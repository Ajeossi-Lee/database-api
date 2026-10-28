from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from pydantic.config import ConfigDict


class UserBase(BaseModel):
    """Base schema for User model."""

    username: str = Field(..., description="Username of the user")
    email: Optional[str] = Field(None, description="Email of the user")
    is_active: bool = Field(True, description="Whether the user is active")
    is_superuser: bool = Field(False, description="Whether the user is a superuser")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    roles: List[str] = Field(default_factory=list, description="User roles")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., description="Password for the user")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class UserUpdate(UserBase):
    """Schema for updating a user."""

    password: Optional[str] = Field(None, description="New password for the user")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class UserRead(UserBase):
    """Schema for reading a user."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class RegisterRequest(BaseModel):
    """自助注册。不能指定超级用户、角色或权限。"""

    username: str = Field(..., min_length=1, max_length=255, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class RefreshRequest(BaseModel):
    """用刷新令牌换取新令牌。"""

    refresh_token: str = Field(..., description="刷新令牌")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class LogoutRequest(BaseModel):
    """退出时可选地带上刷新令牌，以便一并失效。"""

    refresh_token: Optional[str] = Field(None, description="刷新令牌")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )