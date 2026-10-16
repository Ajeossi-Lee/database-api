from enum import Enum
from typing import List, Optional, Literal
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