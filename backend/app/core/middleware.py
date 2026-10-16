from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
import time
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to handle request timeouts."""

    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        # Set timeout for the request
        start_time = time.time()

        try:
            response = await call_next(request)

            # Log request duration
            duration = time.time() - start_time
            logger.debug(f"Request {request.url.path} took {duration:.2f}s")

            return response

        except Exception as exc:
            duration = time.time() - start_time
            logger.warning(f"Request {request.url.path} failed after {duration:.2f}s: {exc}")
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request IDs to requests and responses."""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or f"req_{int(time.time())}_{id(request)}"
        request.state.request_id = request_id

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


# Rate limiting configuration
def configure_rate_limiting(app):
    """Configure rate limiting for the application."""
    app.add_middleware(BaseHTTPMiddleware, dispatch=limiter.middleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)