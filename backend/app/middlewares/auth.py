from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.security import User, apply_route_policy
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.settings.config import settings


async def enforce_auth_middleware(request: Request, call_next):
    """按路由策略执行认证。健康检查和文档路径直接放行。"""

    # 健康检查和文档不走认证
    if request.url.path in ["/healthz", "/readyz", "/docs", "/openapi.json"]:
        response = await call_next(request)
        return response

    # 关闭认证时，非生产环境注入演示用户，生产环境直接失败
    if not settings.AUTH_ENABLED:
        if settings.APP_ENV != "prod":
            mock_user = User(
                id="mock-user-id",
                username="developer",
                email="developer@example.com",
                is_active=True,
                is_superuser=False,
                permissions=["*:*"],
                roles=["admin"]
            )
            request.state.user = mock_user
            response = await call_next(request)
            return response
        else:
            raise HTTPException(
                status_code=500,
                detail="Authentication is disabled in production environment"
            )

    # 路由策略由 policy() 依赖在进入接口前执行。中间件比依赖更早，这里还读不到。
    route_policy = getattr(request.state, "route_policy", None)
    if route_policy is None:
        return await call_next(request)

    try:
        await apply_route_policy(request, route_policy)
    except (UnauthorizedException, ForbiddenException):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return await call_next(request)


class EnforceAuthMiddleware(BaseHTTPMiddleware):
    """把认证策略函数挂到中间件链上。"""

    async def dispatch(self, request: Request, call_next):
        return await enforce_auth_middleware(request, call_next)
