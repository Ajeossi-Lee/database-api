from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.genes.service import GeneService


def get_gene_service(db: AsyncSession = Depends(get_db)):
    """Dependency to get GeneService."""
    return GeneService(db)