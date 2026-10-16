from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware
from app.core.security import SecurityHeadersMiddleware
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

    # Add middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
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
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

# Create the application instance
app = create_app()