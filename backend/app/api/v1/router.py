from fastapi import APIRouter
from app.modules.genes.router import router as genes_router
from app.core.health import router as health_router

# Create the API router
api_router = APIRouter(prefix="/api/v1")

# Include module routers
api_router.include_router(genes_router, prefix="/genes", tags=["genes"])
api_router.include_router(health_router, prefix="", tags=["health"])