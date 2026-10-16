"""Base schemas for the application."""

from pydantic import BaseModel
from pydantic.config import ConfigDict
from typing import Optional


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        # Add other common configurations as needed
    )


class BaseCreateSchema(BaseSchema):
    """Base schema for creating entities."""
    pass


class BaseUpdateSchema(BaseSchema):
    """Base schema for updating entities."""
    pass


class BaseReadSchema(BaseSchema):
    """Base schema for reading entities."""
    pass