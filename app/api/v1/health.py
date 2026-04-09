"""
Health check endpoints.

- GET /health/live  — liveness probe (is the process alive?)
- GET /health/ready — readiness probe (can we serve traffic? DB reachable?)
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Liveness probe")
async def liveness() -> dict:
    """Returns 200 if the process is running. No dependencies checked."""
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ready", summary="Readiness probe")
async def readiness(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Returns 200 if the API is ready to serve traffic (DB reachable)."""
    await db.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {"database": "ok"},
    }
