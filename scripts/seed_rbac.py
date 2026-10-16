"""
Script to seed initial RBAC data for the application.
This script creates default roles and permissions.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.config import settings
from app.db.base import Base
from app.db.session import AsyncSessionFactory


async def seed_rbac():
    """Seed initial RBAC data."""

    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSessionFactory() as session:
        try:
            # Create tables if they don't exist
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            print("RBAC seeding completed successfully!")
        except Exception as e:
            print(f"Error during RBAC seeding: {e}")
            raise
        finally:
            await session.close()
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_rbac())