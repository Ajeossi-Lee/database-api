from fastapi import APIRouter, Depends
from app.modules.genes.service import GeneService
from app.modules.genes.schemas import GeneCreate, GeneUpdate, GeneRead
from app.db.session import get_db

router = APIRouter()

@router.get("/genes/{gene_id}", response_model=GeneRead)
async def get_gene(
    gene_id: str,
    service: GeneService = Depends(GeneService),
):
    """Get a gene by ID."""
    return await service.get_gene(gene_id)

@router.get("/genes", response_model=list[GeneRead])
async def list_genes(
    service: GeneService = Depends(GeneService),
):
    """List genes."""
    return await service.list_genes()

@router.post("/genes", response_model=GeneRead)
async def create_gene(
    gene: GeneCreate,
    service: GeneService = Depends(GeneService),
):
    """Create a new gene."""
    return await service.create_gene(gene)

@router.put("/genes/{gene_id}", response_model=GeneRead)
async def update_gene(
    gene_id: str,
    gene: GeneUpdate,
    service: GeneService = Depends(GeneService),
):
    """Update a gene."""
    return await service.update_gene(gene_id, gene)

@router.delete("/genes/{gene_id}")
async def delete_gene(
    gene_id: str,
    service: GeneService = Depends(GeneService),
):
    """Delete a gene."""
    await service.delete_gene(gene_id)
    return {"message": "Gene deleted successfully"}