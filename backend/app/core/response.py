from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from pydantic.config import ConfigDict

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """Unified response model for API responses."""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class PageParams(BaseModel):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class PageResult(BaseModel, Generic[T]):
    """Pagination result model."""

    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )