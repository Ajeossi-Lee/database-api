from fastapi import Depends
from app.db.session import get_db
from app.core.response import PageParams
from sqlalchemy.ext.asyncio import AsyncSession


async def get_page_params(
    page: int = 1,
    page_size: int = 10
) -> PageParams:
    """Dependency to get pagination parameters."""
    return PageParams(page=page, page_size=page_size)


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    async for session in get_db():
        yield session