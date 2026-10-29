from fastapi import Depends, Query
from app.db.session import get_db
from app.core.response import PageParams
from app.modules.genes.service import GeneService
from sqlalchemy.ext.asyncio import AsyncSession


async def get_page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PageParams:
    """读取分页参数。页码从 1 开始，每页最多 100 条。"""
    return PageParams(page=page, page_size=page_size)


async def get_db_session() -> AsyncSession:
    """Dependency to get database session."""
    async for session in get_db():
        yield session


async def get_gene_service(session: AsyncSession = Depends(get_db)) -> GeneService:
    """用当前请求的数据库会话创建基因服务。"""
    return GeneService(session)