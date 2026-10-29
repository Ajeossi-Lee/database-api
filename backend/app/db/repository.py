from __future__ import annotations

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

    def _apply_alive(self, stmt, include_deleted: bool = False):
        """模型有 deleted_at 时默认不查出已删除行。"""
        if include_deleted or not hasattr(self.model, "deleted_at"):
            return stmt
        return stmt.where(self.model.deleted_at.is_(None))

    async def get(self, id: UUID, include_deleted: bool = False) -> Optional[ModelType]:
        """Get an object by ID."""
        stmt = self._apply_alive(select(self.model).where(self.model.id == id), include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_including_deleted(self, id: UUID) -> Optional[ModelType]:
        """按 ID 获取对象，包含已软删除的行。"""
        return await self.get(id, include_deleted=True)

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[ModelType]:
        """Get multiple objects with pagination."""
        stmt = self._apply_alive(select(self.model).offset(skip).limit(limit), include_deleted)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_create: dict) -> ModelType:
        """Create a new object."""
        obj = self.model(**obj_create)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(
        self,
        id: UUID,
        obj_update: dict,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """Update an existing object."""
        stmt = self._apply_alive(
            update(self.model).where(self.model.id == id).values(**obj_update),
            include_deleted,
        )
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            return None

        await self.session.flush()
        # Get the updated object
        return await self.get(id, include_deleted=include_deleted)

    async def delete(self, id: UUID, include_deleted: bool = False) -> bool:
        """Delete an object."""
        stmt = self._apply_alive(delete(self.model).where(self.model.id == id), include_deleted)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def count(self, include_deleted: bool = False) -> int:
        """Count all objects."""
        stmt = self._apply_alive(select(func.count(self.model.id)), include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, id: UUID, include_deleted: bool = False) -> bool:
        """Check if an object exists."""
        stmt = self._apply_alive(select(self.model.id).where(self.model.id == id), include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_paginated(
        self,
        page_params: PageParams,
        include_deleted: bool = False,
    ) -> PageResult[ModelType]:
        """Get paginated results."""
        skip = (page_params.page - 1) * page_params.page_size

        # Get total count
        total_stmt = self._apply_alive(select(func.count(self.model.id)), include_deleted)
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one()

        # Get items
        items_stmt = self._apply_alive(
            select(self.model).offset(skip).limit(page_params.page_size),
            include_deleted,
        )
        items_result = await self.session.execute(items_stmt)
        items = items_result.scalars().all()

        return PageResult(
            items=items,
            total=total,
            page=page_params.page,
            page_size=page_params.page_size
        )