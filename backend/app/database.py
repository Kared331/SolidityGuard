"""Unified database engine module (3.9).

Provides singleton sync and async engines so that every task, route, and
service imports from one place instead of each creating its own engine.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import logger, settings

# ─── Async engine (for FastAPI routes) ──────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)
async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# ─── Sync engine (for Celery tasks & Alembic) ───────────────────
sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
sync_engine = create_engine(
    sync_url,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)
sync_session_factory = sessionmaker(bind=sync_engine)


def get_sync_session() -> Session:
    """Return a new sync Session from the shared pool."""
    return sync_session_factory()


class Base(DeclarativeBase):
    pass


logger.info("Database engines initialised (%s)", sync_url.split("@")[-1] if "@" in sync_url else sync_url)
