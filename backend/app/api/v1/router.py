from fastapi import APIRouter

from app.core.response import COMMON_ERROR_RESPONSES
from app.modules.genes.router import router as genes_router
from app.modules.users.router import router as users_router

# Create the API router
api_router = APIRouter(prefix="/api/v1")

# Include module routers
api_router.include_router(
    genes_router,
    prefix="/genes",
    tags=["genes"],
    responses=COMMON_ERROR_RESPONSES,
)
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
    responses=COMMON_ERROR_RESPONSES,
)
