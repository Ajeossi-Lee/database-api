#!/usr/bin/env python3
"""
Script to seed initial RBAC data for the application.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.modules.users.models import User
from app.core.security import hash_password_util
from uuid import uuid4


async def seed_initial_users():
    """Seed initial users with roles and permissions."""

    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if admin user already exists
            result = await session.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            )
            existing_admin = result.fetchone()

            if not existing_admin:
                # Create admin user
                admin_user = User(
                    id=uuid4(),
                    username="admin",
                    email="admin@example.com",
                    hashed_password=hash_password_util("admin123"),
                    is_active=True,
                    is_superuser=True,
                    permissions=["*:*"],
                    roles=["admin"]
                )
                session.add(admin_user)
                print("Created admin user")

            # Check if curator user already exists
            result = await session.execute(
                "SELECT id FROM users WHERE username = 'curator'"
            )
            existing_curator = result.fetchone()

            if not existing_curator:
                # Create curator user
                curator_user = User(
                    id=uuid4(),
                    username="curator",
                    email="curator@example.com",
                    hashed_password=hash_password_util("curator123"),
                    is_active=True,
                    is_superuser=False,
                    permissions=["gene:*", "user:manage"],
                    roles=["curator"]
                )
                session.add(curator_user)
                print("Created curator user")

            # Check if viewer user already exists
            result = await session.execute(
                "SELECT id FROM users WHERE username = 'viewer'"
            )
            existing_viewer = result.fetchone()

            if not existing_viewer:
                # Create viewer user
                viewer_user = User(
                    id=uuid4(),
                    username="viewer",
                    email="viewer@example.com",
                    hashed_password=hash_password_util("viewer123"),
                    is_active=True,
                    is_superuser=False,
                    permissions=["gene:read"],
                    roles=["viewer"]
                )
                session.add(viewer_user)
                print("Created viewer user")

            await session.commit()
            print("Successfully seeded RBAC data")

        except Exception as e:
            await session.rollback()
            print(f"Error seeding RBAC data: {e}")
            raise
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(seed_initial_users())