from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.session import engine
from app.settings.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager for startup and shutdown events."""

    # Startup logic
    logger.info("Starting up application...")

    # Check database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Load authentication policy configuration if needed
    # This would be where we load auth policies from YAML or database

    # Yield control to the application
    yield

    # Shutdown logic
    logger.info("Shutting down application...")

    # Dispose the database engine
    await engine.dispose()
    logger.info("Database engine disposed")