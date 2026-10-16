from typing import TypeVar, Generic, List, Optional, Type
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func
from app.db.base import Base
from app.core.response import PageParams, PageResult


ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository base class with common operations."""

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: UUID) -> Optional[ModelType]:
        """Get an object by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple objects with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_create: dict) -> ModelType:
        """Create a new object."""
        obj = self.model(**obj_create)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: UUID, obj_update: dict) -> Optional[ModelType]:
        """Update an existing object."""
        stmt = update(self.model).where(self.model.id == id).values(**obj_update)
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            return None

        await self.session.commit()
        # Get the updated object
        return await self.get(id)

    async def delete(self, id: UUID) -> bool:
        """Delete an object."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count all objects."""
        stmt = select(func.count(self.model.id))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, id: UUID) -> bool:
        """Check if an object exists."""
        stmt = select(self.model.id).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_paginated(self, page_params: PageParams) -> PageResult[ModelType]:
        """Get paginated results."""
        skip = (page_params.page - 1) * page_params.page_size

        # Get total count
        total_stmt = select(func.count(self.model.id))
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one()

        # Get items
        items_stmt = select(self.model).offset(skip).limit(page_params.page_size)
        items_result = await self.session.execute(items_stmt)
        items = items_result.scalars().all()

        return PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size
        )