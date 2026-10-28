import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.settings.config import settings

logger = logging.getLogger(__name__)

# Create the async engine with proper connection pooling configuration
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # 调试模式下回显 SQL。日志配置会让这些语句只出现在控制台。
    echo=settings.DEBUG
)

def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """记录查询开始时间，供慢查询判断使用。"""
    context._query_start_time = time.perf_counter()


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """超过 LOG_MIN_DURATION_STATEMENT 时记录慢查询，不记录参数。"""
    start = getattr(context, "_query_start_time", None)
    if start is None:
        return
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms >= settings.LOG_MIN_DURATION_STATEMENT:
        logger.warning("慢查询 duration_ms=%.0f statement=%s", elapsed_ms, statement)


event.listens_for(engine.sync_engine, "before_cursor_execute")(_before_cursor_execute)
event.listens_for(engine.sync_engine, "after_cursor_execute")(_after_cursor_execute)

# Create the async session factory
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()