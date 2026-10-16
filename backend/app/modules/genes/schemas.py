from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class GeneBase(BaseModel):
    """Base schema for Gene model."""

    name: str = Field(..., description="Name of the gene")
    description: Optional[str] = Field(None, description="Description of the gene")


class GeneCreate(GeneBase):
    """Schema for creating a gene."""
    pass


class GeneUpdate(GeneBase):
    """Schema for updating a gene."""
    pass


class GeneRead(GeneBase):
    """Schema for reading a gene."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }