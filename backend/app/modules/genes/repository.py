from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.genes.models import Gene
from app.modules.genes.schemas import GeneCreate, GeneUpdate


class GeneRepository:
    """Repository for Gene entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_gene(self, gene_id: UUID) -> Optional[Gene]:
        """Get a gene by ID."""
        stmt = select(Gene).where(Gene.id == gene_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_genes(self) -> List[Gene]:
        """List all genes."""
        stmt = select(Gene)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_gene(self, gene_create: GeneCreate) -> Gene:
        """Create a new gene."""
        gene = Gene(**gene_create.model_dump())
        self.session.add(gene)
        await self.session.commit()
        await self.session.refresh(gene)
        return gene

    async def update_gene(self, gene_id: UUID, gene_update: GeneUpdate) -> Optional[Gene]:
        """Update a gene."""
        gene = await self.get_gene(gene_id)
        if gene:
            for field, value in gene_update.model_dump(exclude_unset=True).items():
                setattr(gene, field, value)
            await self.session.commit()
            await self.session.refresh(gene)
        return gene

    async def delete_gene(self, gene_id: UUID) -> bool:
        """Delete a gene."""
        gene = await self.get_gene(gene_id)
        if gene:
            await self.session.delete(gene)
            await self.session.commit()
            return True
        return False