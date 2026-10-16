#!/usr/bin/env python3
"""
Graceful shutdown helper for the application.
"""

import signal
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for graceful shutdown."""

    # Startup logic
    logger.info("Starting application...")

    # Initialize database connection pool
    try:
        # Test database connection
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown logic
    logger.info("Shutting down application gracefully...")

    # Close database connections
    try:
        await engine.dispose()
        logger.info("Database connections disposed")
    except Exception as e:
        logger.error(f"Error disposing database connections: {e}")

    logger.info("Application shutdown complete")

# This function can be used to handle SIGTERM/SIGINT signals
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)