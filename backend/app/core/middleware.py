import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to requests and logs."""

    async def dispatch(self, request: Request, call_next):
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind request ID to logger
        logger = structlog.get_logger()
        request.state.logger = logger.bind(request_id=request_id)

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response