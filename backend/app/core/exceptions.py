import logging
import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.settings.config import settings

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用异常基类。code 沿用数字错误码，details 放上下文。"""

    def __init__(
        self,
        code: int = 0,
        message: str = "An error occurred",
        status_code: int = 500,
        request_id: Optional[str] = None,
        details: Any = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id or str(uuid.uuid4())
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(code=404, message=message, status_code=404)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(code=409, message=message, status_code=409)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(code=401, message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(code=403, message=message, status_code=403)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(code=422, message=message, status_code=422)


def _request_id(request: Request, fallback: Optional[str] = None) -> str:
    """优先使用中间件写入的请求 ID，保证响应体和 X-Request-ID 一致。"""
    state_id = getattr(request.state, "request_id", None)
    if state_id:
        return str(state_id)
    return fallback or str(uuid.uuid4())


def _error_content(
    *,
    code: int,
    message: str,
    request_id: str,
    details: Any = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    """组装统一错误体。调试模式下才附带 error。"""
    content: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
        "details": details,
    }
    if settings.DEBUG and error is not None:
        content["error"] = error
    return content


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    """抽出字段位置和原因，避免把不可序列化的上下文写进响应。"""
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        details.append(
            {
                "loc": [str(part) for part in err.get("loc", ())],
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )
    return details


def _http_exception_message(detail: Any) -> tuple[str, Any]:
    """字符串 detail 作为 message；结构化 detail 放进 details。"""
    if isinstance(detail, str):
        return detail, None
    return "Request failed", detail


def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器，让业务异常、HTTP 异常和参数校验使用同一错误体。"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理应用自定义异常。"""
        request_id = _request_id(request, exc.request_id)
        logger.warning(
            "业务异常 request_id=%s code=%s status=%s message=%s",
            request_id,
            exc.code,
            exc.status_code,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_content(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
                details=exc.details,
                error=str(exc),
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """把 FastAPI 的 HTTPException 收成统一错误体。"""
        message, details = _http_exception_message(exc.detail)
        request_id = _request_id(request)
        logger.warning(
            "HTTP 异常 request_id=%s status=%s message=%s",
            request_id,
            exc.status_code,
            message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_content(
                code=exc.status_code,
                message=message,
                request_id=request_id,
                details=details,
                error=str(exc),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """把参数校验失败收成统一错误体，字段错误放在 details。"""
        request_id = _request_id(request)
        details = _validation_details(exc)
        logger.warning(
            "参数校验失败 request_id=%s details=%s",
            request_id,
            details,
        )
        return JSONResponse(
            status_code=422,
            content=_error_content(
                code=422,
                message="Validation error",
                request_id=request_id,
                details=details,
                error=str(exc),
            ),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理未捕获异常。非调试模式不返回内部错误内容。"""
        request_id = _request_id(request)
        logger.exception("未捕获异常 request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content=_error_content(
                code=500,
                message="Internal server error",
                request_id=request_id,
                details=None,
                error=str(exc),
            ),
        )
