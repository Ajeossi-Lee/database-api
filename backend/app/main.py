from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from app.middlewares.request import RequestIDMiddleware, configure_rate_limiting
from app.middlewares.security_headers import SecurityHeadersMiddleware as CustomSecurityHeadersMiddleware
from app.modules.health.router import router as health_router
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
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 先挂限流，再挂请求 ID，这样超限响应也能带上 X-Request-ID
    configure_rate_limiting(app)

    # Add middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(CustomSecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Add CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        )

    # Register exception handlers
    register_exception_handlers(app)

    # 探针在根路径。业务路由自身已带 /api/v1
    app.include_router(health_router)
    app.include_router(api_router)

    return app

# Create the application instance
app = create_app()