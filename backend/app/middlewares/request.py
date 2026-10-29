import logging
import re
import time
import uuid

from app.core.exceptions import _error_content, _request_id
from app.core.logging import request_id_var
from app.settings.config import settings
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware
from slowapi.util import get_remote_address
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

# 只接受可见的请求 ID，避免把换行写进日志。
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _incoming_request_id(request: Request) -> str:
    """采用调用方传来的安全请求 ID，否则生成 UUID。"""
    incoming = request.headers.get("X-Request-ID", "")
    if _REQUEST_ID_RE.fullmatch(incoming):
        return incoming
    return str(uuid.uuid4())

# 按当前配置创建限流器。configure_rate_limiting 会按开关决定是否挂上
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])

class RequestIDMiddleware:
    """为每个请求分配 ID，并写入日志上下文。使用原生 ASGI，避免上下文在子任务里丢失。"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = _incoming_request_id(request)
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        start_time = time.time()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            duration = time.time() - start_time
            logger.exception(
                "请求失败 method=%s path=%s duration=%.2fs",
                request.method,
                request.url.path,
                duration,
            )
            raise
        else:
            duration = time.time() - start_time
            logger.info(
                "请求完成 method=%s path=%s status=%s duration=%.2fs",
                request.method,
                request.url.path,
                status_code,
                duration,
            )
        finally:
            request_id_var.reset(token)


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