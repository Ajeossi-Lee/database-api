from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate
from app.core.exceptions import NotFoundException, ConflictException
from app.core.security import authenticate_user


class UserService:
    """Service for User entities."""

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        user = await self.repository.get_user(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        user = await self.repository.get_user_by_username(username)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users."""
        return await self.repository.list_users(skip, limit)

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.repository.get_user_by_username(user_create.username)
        if existing_user:
            raise ConflictException("User with this username already exists")

        existing_email = await self.repository.get_user_by_email(user_create.email)
        if existing_email:
            raise ConflictException("User with this email already exists")

        return await self.repository.create_user(user_create)

    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
        """Update a user."""
        user = await self.get_user(user_id)
        return await self.repository.update_user(user_id, user_update)

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        user = await self.get_user(user_id)
        return await self.repository.delete_user(user_id)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        return await authenticate_user(username, password)