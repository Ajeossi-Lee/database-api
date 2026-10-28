import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

# 前缀由 api/v1/router.py 的 include_router(..., prefix="") 提供
router = APIRouter()


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    """存活检查：进程能响应即视为健康。"""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": settings.PROJECT_NAME}
    )


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """就绪检查：确认数据库可连接，并返回连接池状态。"""
    try:
        # 检查数据库是否可连接
        await db.execute(text("SELECT 1"))

        # 读取连接池状态
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
