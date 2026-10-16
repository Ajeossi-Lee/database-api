from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.config import settings

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
        await db.execute("SELECT 1")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "service": settings.PROJECT_NAME}
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unready", "service": settings.PROJECT_NAME}
        )