"""
Alembic migration environment.

Supports both offline (generate SQL script) and online (run against live DB) modes.
Uses asyncpg via a sync-shim for Alembic compatibility.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

# Import all models so Alembic can detect schema changes via Base.metadata
from app.models.base import Base
from app.models.document import Document  # noqa: F401
from app.models.extraction import ExtractionResult  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.pii_mapping import PIIMapping  # noqa: F401
from app.models.review import ReviewTask, ReviewDecision  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Read DATABASE_URL from env, converting asyncpg → psycopg2 for Alembic sync mode."""
    import os
    url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
    # Alembic needs a sync driver; swap asyncpg for psycopg2
    return url.replace("postgresql+asyncpg://", "postgresql://")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    url = get_url().replace("postgresql://", "postgresql+asyncpg://")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
