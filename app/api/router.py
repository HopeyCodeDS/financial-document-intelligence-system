"""
Aggregates all v1 API routers into a single router mounted at /api/v1.

Note: the health router is intentionally NOT included here. Liveness and
readiness probes are operational endpoints, not part of the versioned API
surface, and are mounted unprefixed in app.main.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.extractions import router as extractions_router
from app.api.v1.review import router as review_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(extractions_router)
api_router.include_router(review_router)
api_router.include_router(audit_router)
