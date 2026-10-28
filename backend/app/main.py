from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from app.middlewares.auth import EnforceAuthMiddleware
from app.middlewares.request import RequestIDMiddleware, configure_rate_limiting
from app.middlewares.security_headers import (
    FileUploadSecurityMiddleware,
    SQLInjectionProtectionMiddleware,
)
from app.middlewares.security_headers import (
    SecurityHeadersMiddleware as CustomSecurityHeadersMiddleware,
)
from app.settings.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 先挂限流，再挂请求 ID，这样超限响应也能带上 X-Request-ID
    configure_rate_limiting(app)

    # Add middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(CustomSecurityHeadersMiddleware)
    app.add_middleware(SQLInjectionProtectionMiddleware)
    app.add_middleware(FileUploadSecurityMiddleware)
    app.add_middleware(EnforceAuthMiddleware)  # Authentication enforcement middleware
    app.add_middleware(GZipMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # Add CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register exception handlers
    register_exception_handlers(app)

    # Include API routes
    # api_router 自身已带 /api/v1，这里不再重复加前缀
    app.include_router(api_router)

    return app

# Create the application instance
app = create_app()