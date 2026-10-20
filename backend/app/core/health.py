from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": settings.PROJECT_NAME}
    )


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check endpoint - verifies database connectivity."""
    try:
        # Test database connectivity
        await db.execute(text("SELECT 1"))

        # Test connection pool status
        # This is a simple check - in production you might want more sophisticated checks
        engine = db.bind
        if hasattr(engine, 'pool'):
            pool_status = {
                'checked': True,
                'size': engine.pool.size(),
                'checkedout': engine.pool.checkedout(),
                'overflow': engine.pool.overflow()
            }
        else:
            pool_status = {"checked": False}

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "service": settings.PROJECT_NAME,
                "database": "connected",
                "connection_pool": pool_status
            }
        )
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "service": settings.PROJECT_NAME,
                "error": str(e)
            }
        )