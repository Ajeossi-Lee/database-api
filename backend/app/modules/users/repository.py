from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.auth.security import hash_password


class UserRepository:
    """Repository for User entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users."""
        stmt = select(User).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        # Hash the password
        hashed_password = await hash_password(user_create.password)

        # Create user object
        user_data = user_create.model_dump()
        user_data.pop("password")  # Remove password from data
        user_data["hashed_password"] = hashed_password

        user = User(**user_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
        """Update a user."""
        # Check if password is being updated
        if user_update.password:
            hashed_password = await hash_password(user_update.password)
            user_update_dict = user_update.model_dump(exclude_unset=True)
            user_update_dict["hashed_password"] = hashed_password
        else:
            user_update_dict = user_update.model_dump(exclude_unset=True)

        stmt = update(User).where(User.id == user_id).values(**user_update_dict)
        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            return None

        await self.session.commit()
        # Get the updated user
        return await self.get_user(user_id)

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False

    async def exists(self, user_id: UUID) -> bool:
        """Check if a user exists."""
        stmt = select(User.id).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None