import logging
import time

from app.core.exceptions import _error_content, _request_id
from app.settings.config import settings
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 按当前配置创建限流器。configure_rate_limiting 会按开关决定是否挂上
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request IDs to requests and responses."""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or f"req_{int(time.time())}_{id(request)}"
        request.state.request_id = request_id
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception:
            duration = time.time() - start_time
            logger.exception(
                "请求失败 request_id=%s method=%s path=%s duration=%.2fs",
                request_id,
                request.method,
                request.url.path,
                duration,
            )
            raise

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        duration = time.time() - start_time
        logger.info(
            "请求完成 request_id=%s method=%s path=%s status=%s duration=%.2fs",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """超限时返回与其它错误一致的响应体。"""
    request_id = _request_id(request)
    message = str(exc.detail)
    logger.warning("请求频率超限 request_id=%s message=%s", request_id, message)
    return JSONResponse(
        status_code=429,
        content=_error_content(
            code=429,
            message=message,
            request_id=request_id,
            details=None,
            error=str(exc),
        ),
    )


def configure_rate_limiting(app):
    """按配置开启 slowapi。关闭时不挂中间件，请求频率不受限制。"""
    global limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT],
        enabled=settings.RATE_LIMIT_ENABLED,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    if not settings.RATE_LIMIT_ENABLED:
        return
    app.add_middleware(SlowAPIASGIMiddleware)