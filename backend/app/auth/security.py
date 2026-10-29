import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError as JWTError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.policy import AuthMode, RoutePolicy
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.logging import log_authentication_event, log_authorization_event
from app.db.session import AsyncSessionFactory
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 口令哈希。导入脚本使用同一套算法
pwd_context = PasswordHash.recommended()


# OAuth2 scheme for password bearer
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/users/login",
    auto_error=False,
)


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
    jti: Optional[str] = None


# 当前进程内已吊销的 jti。多进程部署需要换成共享存储。
_revoked_jtis: set[str] = set()


def revoke_jti(jti: Optional[str]) -> None:
    """把令牌编号记为失效。空编号忽略。"""
    if jti:
        _revoked_jtis.add(jti)


def _auth_disabled_user() -> User:
    """关闭认证时使用的演示用户。生产环境由调用方拒绝。"""
    return User(
        id="mock-user-id",
        username="developer",
        email="developer@example.com",
        is_active=True,
        is_superuser=True,
        permissions=["*:*"],
        roles=["admin"],
    )


def _reject_auth_disabled_in_prod() -> None:
    """生产环境不允许关闭认证。"""
    if settings.APP_ENV == "prod":
        raise HTTPException(
            status_code=500,
            detail="Authentication is disabled in production environment",
        )


def _permission_matches(held: str, required: str) -> bool:
    """*:* 放行全部，resource:* 放行该资源，其余精确匹配。"""
    if held == "*:*" or held == required:
        return True
    resource, separator, action = held.partition(":")
    if separator and action == "*" and required.startswith(f"{resource}:"):
        return True
    return False


def _has_permission(user: User, required: str) -> bool:
    held_permissions = user.permissions or []
    return any(_permission_matches(held, required) for held in held_permissions)


def _decode_token(token: str, *, expected_type: str) -> dict:
    """校验签名、签发方、受众、令牌类型和是否已吊销。"""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
    )
    if payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token")
    jti = payload.get("jti")
    if not jti or jti in _revoked_jtis:
        raise UnauthorizedException("Invalid token")
    return payload


def _user_from_record(row) -> User:
    """把用户表记录收成认证用的用户对象。"""
    return User(
        id=str(row.id),
        username=row.username,
        email=row.email,
        is_active=bool(row.is_active),
        is_superuser=bool(row.is_superuser),
        permissions=list(row.permissions or []),
        roles=list(row.roles or []),
    )


def _issue_token(data: dict, expire: datetime, token_type: str) -> str:
    """签发带类型、受众和 jti 的令牌。"""
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": expire,
            "type": token_type,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "jti": str(uuid4()),
        }
    )
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


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
        # 关闭认证时注入演示用户。生产环境直接失败。
        if not settings.AUTH_ENABLED:
            _reject_auth_disabled_in_prod()
            user = _auth_disabled_user()
            request.state.user = user
            return user

        # If no token provided and auth is optional, return None
        if not token and settings.AUTH_DEFAULT_MODE == "optional":
            request.state.user = None
            return None

        # If no token and auth is required, raise unauthorized
        if not token:
            raise UnauthorizedException("Authentication required")

        # 只接受访问令牌。刷新令牌不能调用受保护接口。
        try:
            payload = _decode_token(token, expected_type="access")

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
            request.state.token_jti = payload.get("jti")

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
            _reject_auth_disabled_in_prod()
            user = _auth_disabled_user()
            request.state.user = user
            return user

        if not token:
            request.state.user = None
            return None

        try:
            payload = _decode_token(token, expected_type="access")

            user_id = payload.get("sub")
            if not user_id:
                request.state.user = None
                return None

            user = await get_user_by_id(user_id)
            if not user or not user.is_active:
                request.state.user = None
                return None

            request.state.user = user
            request.state.token_jti = payload.get("jti")
            return user

        except (JWTError, UnauthorizedException):
            request.state.user = None
            return None


async def get_user_by_id(user_id: str) -> Optional[User]:
    """按 ID 从数据库获取认证用户。"""
    if not user_id:
        return None

    try:
        parsed_id = UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        return None

    # 延迟导入，避免用户仓库模块加载 security 时循环引用
    from app.modules.users.models import User as UserRecord

    async with AsyncSessionFactory() as session:
        row = await session.scalar(select(UserRecord).where(UserRecord.id == parsed_id))
    if row is None:
        return None
    return _user_from_record(row)


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """按用户名核对口令。用户不存在、未启用或口令不对时返回空。"""
    from app.modules.users.models import User as UserRecord

    async with AsyncSessionFactory() as session:
        row = await session.scalar(select(UserRecord).where(UserRecord.username == username))
    if row is None:
        return None
    try:
        password_ok = await verify_password(password, row.hashed_password)
    except Exception:
        logger.warning("密码哈希无法校验 username=%s", username)
        return None
    if not password_ok or not row.is_active:
        return None
    return _user_from_record(row)


def _token_expiry(expires_delta: Optional[timedelta], default_minutes: int) -> datetime:
    """计算令牌过期时间。调用方传入的有效期优先。"""
    if expires_delta:
        return datetime.now(timezone.utc) + expires_delta
    return datetime.now(timezone.utc) + timedelta(minutes=default_minutes)


async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create access token."""
    expire = _token_expiry(expires_delta, settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return _issue_token(data, expire, "access")


async def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create refresh token."""
    expire = _token_expiry(expires_delta, settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    return _issue_token(data, expire, "refresh")


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
            log_authorization_event(
                "check",
                user_id=user.id,
                granted=False,
                action=permission_logic,
                details={"message": "Insufficient role permissions"},
            )
            raise ForbiddenException("Insufficient role permissions")

    # Check permissions if required
    if required_permissions:
        if permission_logic == "all":
            # 每一项都必须由精确权限或通配权限满足
            if not all(_has_permission(user, permission) for permission in required_permissions):
                log_authorization_event(
                    "check",
                    user_id=user.id,
                    granted=False,
                    action=permission_logic,
                    details={"message": "Insufficient permissions"},
                )
                raise ForbiddenException("Insufficient permissions")
        elif permission_logic == "any":
            # 至少一项由精确权限或通配权限满足
            if not any(_has_permission(user, permission) for permission in required_permissions):
                log_authorization_event(
                    "check",
                    user_id=user.id,
                    granted=False,
                    action=permission_logic,
                    details={"message": "Insufficient permissions"},
                )
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


def _log_access_denied(request: Request, reason: str) -> None:
    """记录必须登录的接口被拒绝。不记录令牌本身。"""
    client = request.client.host if request.client else None
    log_authentication_event(
        "access",
        request_id=getattr(request.state, "request_id", None),
        ip_address=client,
        success=False,
        details={"path": request.url.path, "reason": reason},
    )


async def _accept_access_token(request: Request, token: str) -> Optional[User]:
    """解析访问令牌并写入请求状态。类型不对或已吊销时抛出未授权。"""
    payload = _decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")
    user = await get_user_by_id(str(user_id))
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    request.state.user = user
    request.state.token_jti = payload.get("jti")
    return user


def _enforce_route_rate_limit(request: Request, route_policy: RoutePolicy) -> None:
    """按路由声明的频率限制计数。已登录时按用户，否则按来源地址。"""
    if not route_policy.rate_limit:
        return
    from limits import parse
    from slowapi.errors import RateLimitExceeded

    from app.middlewares.request import limiter

    user = getattr(request.state, "user", None)
    user_id = getattr(user, "id", None) if user is not None else None
    identity = f"user:{user_id}" if user_id else request.client.host if request.client else "unknown"
    item = parse(route_policy.rate_limit)
    allowed = limiter.limiter.hit(item, request.url.path, identity)
    if not allowed:
        # slowapi 需要带 error_message 的限额对象，不能直接传 limits 的解析结果
        raise RateLimitExceeded(type("RouteLimit", (), {"limit": item, "error_message": str(item)})())


async def apply_route_policy(request: Request, route_policy: RoutePolicy) -> None:
    """按路由上声明的策略校验登录和权限。"""
    if not settings.AUTH_ENABLED:
        _reject_auth_disabled_in_prod()
        if route_policy.auth == AuthMode.PUBLIC:
            request.state.user = None
        else:
            request.state.user = _auth_disabled_user()
        _enforce_route_rate_limit(request, route_policy)
        return

    if route_policy.auth == AuthMode.PUBLIC:
        request.state.user = None
        _enforce_route_rate_limit(request, route_policy)
        return

    token = _bearer_token(request)

    if route_policy.auth == AuthMode.OPTIONAL:
        request.state.user = None
        if not token:
            _enforce_route_rate_limit(request, route_policy)
            return
        try:
            await _accept_access_token(request, token)
        except (JWTError, UnauthorizedException):
            request.state.user = None
        _enforce_route_rate_limit(request, route_policy)
        return

    if route_policy.auth == AuthMode.REQUIRED:
        if not token:
            _enforce_route_rate_limit(request, route_policy)
            _log_access_denied(request, "Authorization header missing or invalid")
            raise UnauthorizedException("Authorization header missing or invalid")
        try:
            user = await _accept_access_token(request, token)
        except JWTError:
            _enforce_route_rate_limit(request, route_policy)
            _log_access_denied(request, "Invalid token")
            raise UnauthorizedException("Invalid token")
        except UnauthorizedException as exc:
            _enforce_route_rate_limit(request, route_policy)
            _log_access_denied(request, exc.message)
            raise
        _enforce_route_rate_limit(request, route_policy)
        if user and (route_policy.permissions or route_policy.roles):
            await check_permissions(
                user,
                route_policy.permissions,
                route_policy.roles,
                route_policy.permission_logic,
            )


async def _issue_token_pair(user: User) -> Token:
    """为已通过认证的用户签发访问令牌和刷新令牌。"""
    access_token = await create_access_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await create_refresh_token(
        data={"sub": user.id, "username": user.username},
        expires_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


# Login endpoint
async def login(username: str, password: str) -> Token:
    """Login endpoint."""
    user = await authenticate_user(username, password)
    if not user:
        log_authentication_event(
            "login",
            success=False,
            details={"username": username},
        )
        raise UnauthorizedException("Incorrect username or password")

    token = await _issue_token_pair(user)
    log_authentication_event(
        "login",
        user_id=user.id,
        success=True,
        details={"username": username},
    )
    return token


async def refresh_tokens(refresh_token: str) -> Token:
    """用刷新令牌换一组新令牌，并让这次提交的刷新令牌失效。"""
    try:
        payload = _decode_token(refresh_token, expected_type="refresh")
    except JWTError:
        raise UnauthorizedException("Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token")
    user = await get_user_by_id(str(user_id))
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    revoke_jti(payload.get("jti"))
    token = await _issue_token_pair(user)
    log_authentication_event(
        "refresh",
        user_id=user.id,
        success=True,
    )
    return token


async def revoke_session(access_jti: Optional[str] = None, refresh_token: Optional[str] = None) -> None:
    """让当前访问令牌失效。如果带了刷新令牌，一并失效。"""
    revoke_jti(access_jti)
    if not refresh_token:
        log_authentication_event("logout", success=True)
        return
    try:
        payload = _decode_token(refresh_token, expected_type="refresh")
    except (JWTError, UnauthorizedException):
        log_authentication_event("logout", success=True, details={"refresh_token": "ignored"})
        return
    revoke_jti(payload.get("jti"))
    log_authentication_event("logout", user_id=payload.get("sub"), success=True)


# Hash password utility (for seeding)
def hash_password_util(password: str) -> str:
    """Utility to hash passwords for seeding."""
    return pwd_context.hash(password)