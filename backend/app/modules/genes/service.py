from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.genes.repository import GeneRepository
from app.modules.genes.schemas import GeneCreate, GeneUpdate
from app.core.exceptions import NotFoundException


class GeneService:
    """Service for Gene entities."""

    def __init__(self, session: AsyncSession):
        self.repository = GeneRepository(session)

    async def get_gene(self, gene_id: UUID) -> Optional[Gene]:
        """Get a gene by ID."""
        gene = await self.repository.get_gene(gene_id)
        if not gene:
            raise NotFoundException("Gene not found")
        return gene

    async def list_genes(self) -> List[Gene]:
        """List all genes."""
        return await self.repository.list_genes()

    async def create_gene(self, gene_create: GeneCreate) -> Gene:
        """Create a new gene."""
        return await self.repository.create_gene(gene_create)

    async def update_gene(self, gene_id: UUID, gene_update: GeneUpdate) -> Optional[Gene]:
        """Update a gene."""
        gene = await self.get_gene(gene_id)
        return await self.repository.update_gene(gene_id, gene_update)

    async def delete_gene(self, gene_id: UUID) -> bool:
        """Delete a gene."""
        gene = await self.get_gene(gene_id)
        return await self.repository.delete_gene(gene_id)