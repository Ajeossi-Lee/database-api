from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.core.schemas import BaseSchema


class GeneBase(BaseSchema):
    """基因的公共字段。"""

    chromosome_id: UUID = Field(..., description="所属染色体 ID")
    name: str = Field(..., description="基因名称")
    description: Optional[str] = Field(None, description="基因描述")
    symbol: Optional[str] = Field(None, description="基因符号")
    synonyms: Optional[List[str]] = Field(default_factory=list, description="同义词")
    strand: Optional[int] = Field(None, description="链方向，1 为正链，-1 为负链")
    start_position: Optional[int] = Field(None, description="起始位置")
    end_position: Optional[int] = Field(None, description="结束位置")
    genomic_coordinates: Optional[dict] = Field(None, description="基因组坐标区间")
    annotations: Optional[dict] = Field(default_factory=dict, description="注释信息")
    functional_description: Optional[str] = Field(None, description="功能描述")


class GeneCreate(GeneBase):
    """创建基因。"""

    pass


class GeneUpdate(BaseSchema):
    """更新基因。未提交的字段保持原值。"""

    chromosome_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    symbol: Optional[str] = None
    synonyms: Optional[List[str]] = None
    strand: Optional[int] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    genomic_coordinates: Optional[dict] = None
    annotations: Optional[dict] = None
    functional_description: Optional[str] = None


class GeneRead(GeneBase):
    """读取基因。"""

    id: UUID
    created_at: datetime
    updated_at: datetime
