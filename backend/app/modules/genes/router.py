from fastapi import APIRouter, Depends

from app.core.auth_policy import AuthMode, policy
from app.core.response import ApiResponse, PageParams, PageResult
from app.modules.genes.deps import get_page_params
from app.modules.genes.schemas import GeneCreate, GeneRead, GeneUpdate
from app.modules.genes.service import GeneService

# 前缀由 api/v1/router.py 的 include_router(..., prefix="/genes") 提供
router = APIRouter()


@router.get(
    "/{gene_id}",
    response_model=ApiResponse[GeneRead],
    dependencies=[Depends(policy(auth=AuthMode.OPTIONAL))],
)
async def get_gene(
    gene_id: str,
    service: GeneService = Depends(GeneService),
):
    """按 ID 获取基因。"""
    gene = await service.get_gene(gene_id)
    return ApiResponse(data=gene)


@router.get(
    "",
    response_model=ApiResponse[PageResult[GeneRead]],
    dependencies=[Depends(policy(auth=AuthMode.OPTIONAL))],
)
async def list_genes(
    page_params: PageParams = Depends(get_page_params),
    service: GeneService = Depends(GeneService),
):
    """分页列出基因。"""
    result = await service.list_genes_paginated(page_params)
    return ApiResponse(data=result)


@router.post(
    "",
    response_model=ApiResponse[GeneRead],
    dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["gene:write"]))],
)
async def create_gene(
    gene: GeneCreate,
    service: GeneService = Depends(GeneService),
):
    """创建基因。"""
    created_gene = await service.create_gene(gene)
    return ApiResponse(data=created_gene)


@router.put(
    "/{gene_id}",
    response_model=ApiResponse[GeneRead],
    dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["gene:write"]))],
)
async def update_gene(
    gene_id: str,
    gene: GeneUpdate,
    service: GeneService = Depends(GeneService),
):
    """更新基因。"""
    updated_gene = await service.update_gene(gene_id, gene)
    return ApiResponse(data=updated_gene)


@router.delete(
    "/{gene_id}",
    response_model=ApiResponse[None],
    dependencies=[Depends(policy(auth=AuthMode.REQUIRED, permissions=["gene:delete"]))],
)
async def delete_gene(
    gene_id: str,
    service: GeneService = Depends(GeneService),
):
    """删除基因。"""
    await service.delete_gene(gene_id)
    return ApiResponse(message="Gene deleted successfully")
