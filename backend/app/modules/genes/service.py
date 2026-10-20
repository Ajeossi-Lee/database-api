from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.response import PageParams, PageResult
from app.modules.genes.models import Gene
from app.modules.genes.repository import GeneRepository
from app.modules.genes.schemas import GeneCreate, GeneUpdate


class GeneService:
    """基因业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.repository = GeneRepository(session)

    async def get_gene(self, gene_id: UUID) -> Gene:
        """按 ID 获取基因，不存在时抛出未找到。"""
        gene = await self.repository.get_gene(gene_id)
        if not gene:
            raise NotFoundException("Gene not found")
        return gene

    async def get_gene_by_name(self, name: str) -> Gene:
        """按名称获取基因，不存在时抛出未找到。"""
        gene = await self.repository.get_gene_by_name(name)
        if not gene:
            raise NotFoundException("Gene not found")
        return gene

    async def list_genes(self, skip: int = 0, limit: int = 100) -> List[Gene]:
        """按偏移量列出基因。"""
        return await self.repository.list_genes(skip, limit)

    async def list_genes_paginated(self, page_params: PageParams) -> PageResult[Gene]:
        """分页列出基因。"""
        return await self.repository.base_repo.get_paginated(page_params)

    async def create_gene(self, gene_create: GeneCreate) -> Gene:
        """创建基因。"""
        return await self.repository.create_gene(gene_create)

    async def update_gene(self, gene_id: UUID, gene_update: GeneUpdate) -> Gene:
        """更新基因。先确认存在，再写入提交的字段。"""
        await self.get_gene(gene_id)
        updated = await self.repository.update_gene(gene_id, gene_update)
        if updated is None:
            raise NotFoundException("Gene not found")
        return updated

    async def delete_gene(self, gene_id: UUID) -> bool:
        """删除基因。先确认存在。"""
        await self.get_gene(gene_id)
        return await self.repository.delete_gene(gene_id)
