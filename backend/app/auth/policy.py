from enum import Enum
from typing import Callable, List, Literal, Optional

from fastapi import Request
from pydantic import BaseModel


class AuthMode(str, Enum):
    """Authentication mode enumeration."""

    PUBLIC = "public"          # Anonymous access, no token parsing
    OPTIONAL = "optional"      # Parse token if present, but don't require it
    REQUIRED = "required"      # Require valid token


class RoutePolicy(BaseModel):
    """Route policy definition."""

    auth: AuthMode = AuthMode.REQUIRED          # Authentication mode
    permissions: List[str] = []                 # Required permissions (e.g., ["gene:read"])
    permission_logic: Literal["all", "any"] = "all"  # Logic for permissions: all or any
    roles: List[str] = []                       # Required roles (optional, can be used with permissions)
    allow_api_key: bool = False                 # Allow API Key authentication
    rate_limit: Optional[str] = None            # Rate limit (e.g., "100/minute")


def policy(
    auth: AuthMode = AuthMode.REQUIRED,
    permissions: Optional[List[str]] = None,
    permission_logic: str = "all",
    roles: Optional[List[str]] = None,
    allow_api_key: bool = False,
    rate_limit: Optional[str] = None,
) -> Callable[[Request], RoutePolicy]:
    """生成路由依赖，把本接口的认证和授权策略放到 request.state。"""

    route_policy = RoutePolicy(
        auth=auth,
        permissions=permissions or [],
        permission_logic=permission_logic,
        roles=roles or [],
        allow_api_key=allow_api_key,
        rate_limit=rate_limit,
    )

    async def enforce_policy(request: Request) -> RoutePolicy:
        # 中间件早于路由依赖，策略必须在这里执行，不能只写到 request.state
        request.state.route_policy = route_policy
        from app.auth.security import apply_route_policy

        await apply_route_policy(request, route_policy)
        return route_policy

    return enforce_policy