from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.genes.models import Gene
from app.modules.genes.schemas import GeneCreate, GeneUpdate


class GeneRepository:
    """基因数据访问。通用增删改查走 BaseRepository，按名称查询单独实现。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.base_repo = BaseRepository(session, Gene)

    async def get_gene(self, gene_id: UUID) -> Optional[Gene]:
        """按 ID 获取基因。"""
        return await self.base_repo.get(gene_id)

    async def get_gene_by_name(self, name: str) -> Optional[Gene]:
        """按名称获取基因。"""
        stmt = select(Gene).where(Gene.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_genes(self, skip: int = 0, limit: int = 100) -> List[Gene]:
        """按偏移量列出基因。"""
        return await self.base_repo.get_multi(skip, limit)

    async def create_gene(self, gene_create: GeneCreate) -> Gene:
        """创建基因。"""
        return await self.base_repo.create(gene_create.model_dump())

    async def update_gene(self, gene_id: UUID, gene_update: GeneUpdate) -> Optional[Gene]:
        """更新基因。"""
        return await self.base_repo.update(gene_id, gene_update.model_dump(exclude_unset=True))

    async def delete_gene(self, gene_id: UUID) -> bool:
        """删除基因。"""
        return await self.base_repo.delete(gene_id)
