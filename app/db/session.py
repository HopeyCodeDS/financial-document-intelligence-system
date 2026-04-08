"""
Async SQLAlchemy engine and session factory.

Usage in FastAPI endpoint:
    async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
        ...

Usage in Celery task (sync context bridging):
    async with get_async_session() as session:
        ...
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str, echo: bool = False) -> None:
    """Initialise the async engine and session factory.

    Must be called once during application startup (FastAPI lifespan).
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,          # recycle connections every 30 min
        pool_pre_ping=True,         # detect stale connections before use
        connect_args={
            "server_settings": {
                "application_name": "fdis-api",
                "jit": "off",       # disable JIT for short-lived queries
            }
        },
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info("database_initialised", url=database_url.split("@")[-1])  # hide creds


async def close_db() -> None:
    """Dispose the engine on application shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("database_connection_pool_closed")


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _engine


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager that provides a transactional session.

    Commits on clean exit, rolls back on exception.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional session."""
    async with get_async_session() as session:
        yield session
