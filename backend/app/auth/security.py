from typing import Optional, List
from uuid import UUID
from enum import Enum
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
from pwdlib import PasswordHash
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.policy import AuthMode, RoutePolicy
from app.settings.config import settings
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.db.session import AsyncSessionFactory, get_db
from app.core.logging import log_authentication_event, log_authorization_event
import secrets
import hashlib
import base64
import re

# 口令哈希。导入脚本使用同一套算法
pwd_context = PasswordHash.recommended()


# OAuth2 scheme for password bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


class User(BaseModel):
    """User model for authentication."""

    id: str
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    permissions: List[str] = []
    roles: List[str] = []


class TokenData(BaseModel):
    """Token data model."""

    username: Optional[str] = None
    user_id: Optional[str] = None


class Token(BaseModel):
    """Token model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token payload model."""

    sub: str
    exp: datetime
    iss: str
    aud: str
    type: str  # access or refresh


class CurrentUser:
    """Dependency to get current authenticated user."""

    def __init__(self, required_permissions: Optional[List[str]] = None,
                 required_roles: Optional[List[str]] = None,
                 permission_logic: str = "all"):
        self.required_permissions = required_permissions or []
        self.required_roles = required_roles or []
        self.permission_logic = permission_logic

    async def __call__(self, request: Request, token: str = Depends(oauth2_scheme)):
        """Get current user from token."""
        # If authentication is disabled, return a mock user for development
        if not settings.AUTH_ENABLED:
            if settings.APP_ENV != "prod":
                # For development, create a mock admin user
                user = User(
                    id="mock-admin-id",
                    username="admin",
                    email="admin@example.com",
                    is_active=True,
                    is_superuser=True,
                    permissions=["*:*"],
                    roles=["admin"]
                )
                request.state.user = user
                return user
            else:
                # Production with auth disabled should fail
                raise HTTPException(
                    status_code=500,
                    detail="Authentication is disabled in production environment"
                )

        # If no token provided and auth is optional, return None
        if not token and settings.AUTH_DEFAULT_MODE == "optional":
            request.state.user = None
            return None

        # If no token and auth is required, raise unauthorized
        if not token:
            raise UnauthorizedException("Authentication required")

        # Verify and decode token
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE
            )

            # Extract user info from payload
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException("Invalid token")

            # Get user from database or cache
            user = await get_user_by_id(user_id)
            if not user or not user.is_active:
                raise UnauthorizedException("User not found or inactive")

            # Store user in request state for downstream use
            request.state.user = user

            # Check permissions if required
            if self.required_permissions or self.required_roles:
                await check_permissions(user, self.required_permissions, self.required_roles, self.permission_logic)

            return user

        except JWTError:
            raise UnauthorizedException("Invalid token")


class OptionalUser:
    """Dependency to get current user if available, or None."""

    async def __call__(self, request: Request, token: str = Depends(oauth2_scheme)):
        """Get current user if token is valid, otherwise return None."""
        if not settings.AUTH_ENABLED:
            if settings.APP_ENV != "prod":
                # For development, create a mock user
                user = User(
                    id="mock-user-id",
                    username="user",
                    email="user@example.com",
                    is_active=True,
                    is_superuser=False,
                    permissions=[],
                    roles=[]
                )
                request.state.user = user
                return user
            else:
                # Production with auth disabled should fail
                raise HTTPException(
                    status_code=500,
                    detail="Authentication is disabled in production environment"
                )

        if not token:
            request.state.user = None
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE
            )

            user_id = payload.get("sub")
            if not user_id:
                request.state.user = None
                return None

            user = await get_user_by_id(user_id)
            if not user or not user.is_active:
                request.state.user = None
                return None

            request.state.user = user
            return user

        except JWTError:
            request.state.user = None
            return None


# Mock user storage (in production, this would be a real database)
_mock_users = {
    "admin": User(
        id="admin-id",
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_superuser=True,
        permissions=["*:*"],
        roles=["admin"]
    ),
    "curator": User(
        id="curator-id",
        username="curator",
        email="curator@example.com",
        is_active=True,
        is_superuser=False,
        permissions=["gene:*", "user:manage"],
        roles=["curator"]
    ),
    "viewer": User(
        id="viewer-id",
        username="viewer",
        email="viewer@example.com",
        is_active=True,
        is_superuser=False,
        permissions=["gene:read"],
        roles=["viewer"]
    )
}


async def get_user_by_id(user_id: str) -> Optional[User]:
    """按 ID 获取认证用户。数据库里没有时，再查内存中的演示账号。"""
    if not user_id:
        return None

    parsed_id = None
    try:
        parsed_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        parsed_id = None

    if parsed_id is not None:
        # 延迟导入，避免用户仓库模块加载 security 时循环引用
        from app.modules.users.models import User as UserRecord

        async with AsyncSessionFactory() as session:
            row = await session.scalar(select(UserRecord).where(UserRecord.id == parsed_id))
        if row is not None:
            return User(
                id=str(row.id),
                username=row.username,
                email=row.email,
                is_active=bool(row.is_active),
                is_superuser=bool(row.is_superuser),
                permissions=list(row.permissions or []),
                roles=list(row.roles or []),
            )

    for mock_user in _mock_users.values():
        if mock_user.id == user_id:
            return mock_user
    return None


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user."""
    # In a real implementation, this would query the database
    # For now, we'll mock it with our predefined users
    user = _mock_users.get(username)
    if not user:
        return None

    # In a real implementation, we'd verify password hash
    # For demo, we'll just return the user
    return user


async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


async def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


async def check_permissions(user: User, required_permissions: List[str],
                           required_roles: List[str], permission_logic: str = "all") -> None:
    """Check if user has required permissions and roles."""

    # Superusers bypass all permission checks
    if user.is_superuser:
        return

    # Check roles if required
    if required_roles:
        # User must have at least one of the required roles
        if not any(role in user.roles for role in required_roles):
            raise ForbiddenException("Insufficient role permissions")

    # Check permissions if required
    if required_permissions:
        if permission_logic == "all":
            # All permissions must be satisfied
            if not all(permission in user.permissions for permission in required_permissions):
                raise ForbiddenException("Insufficient permissions")
        elif permission_logic == "any":
            # At least one permission must be satisfied
            if not any(permission in user.permissions for permission in required_permissions):
                raise ForbiddenException("Insufficient permissions")


async def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _bearer_token(request: Request) -> Optional[str]:
    """取出 Authorization 头里的 Bearer 令牌。没有或格式不对时返回空。"""
    header = request.headers.get("authorization")
    if not header or not header.startswith("Bearer "):
        return None
    return header[7:]


async def apply_route_policy(request: Request, route_policy: RoutePolicy) -> None:
    """按路由上声明的策略校验登录和权限。"""
    if route_policy.auth == AuthMode.PUBLIC:
        request.state.user = None
        return

    token = _bearer_token(request)

    if route_policy.auth == AuthMode.OPTIONAL:
        request.state.user = None
        if not token:
            return
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
            user_id = payload.get("sub")
            if not user_id:
                return
            user = await get_user_by_id(user_id)
            if user and user.is_active:
                request.state.user = user
        except JWTError:
            request.state.user = None
        return

    if route_policy.auth == AuthMode.REQUIRED:
        if not token:
            raise UnauthorizedException("Authorization header missing or invalid")
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
            )
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException("Invalid token")
            user = await get_user_by_id(user_id)
            if not user or not user.is_active:
                raise UnauthorizedException("User not found or inactive")
            request.state.user = user
            if route_policy.permissions or route_policy.roles:
                await check_permissions(
                    user,
                    route_policy.permissions,
                    route_policy.roles,
                    route_policy.permission_logic,
                )
        except JWTError:
            raise UnauthorizedException("Invalid token")


# Login endpoint
async def login(username: str, password: str) -> Token:
    """Login endpoint."""
    user = await authenticate_user(username, password)
    if not user:
        raise UnauthorizedException("Incorrect username or password")

    # Create access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token_expires = timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = await create_refresh_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=refresh_token_expires
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


# Hash password utility (for seeding)
def hash_password_util(password: str) -> str:
    """Utility to hash passwords for seeding."""
    return pwd_context.hash(password)