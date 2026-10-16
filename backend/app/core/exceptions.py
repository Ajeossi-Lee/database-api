from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Optional
from app.core.config import settings
import uuid


class AppException(Exception):
    """Base exception for the application."""

    def __init__(
        self,
        code: int = 0,
        message: str = "An error occurred",
        status_code: int = 500,
        request_id: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id or str(uuid.uuid4())
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


def register_exception_handlers(app: FastAPI):
    """Register global exception handlers."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle custom application exceptions."""
        if settings.DEBUG:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": exc.request_id,
                    "error": str(exc)
                }
            )
        else:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": exc.request_id
                }
            )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        if settings.DEBUG:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "Internal server error",
                    "request_id": str(uuid.uuid4()),
                    "error": str(exc)
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "message": "Internal server error",
                    "request_id": str(uuid.uuid4())
                }
            )