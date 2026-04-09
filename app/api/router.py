"""
Aggregates all v1 API routers into a single router mounted at /api/v1.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

# Health is unauthenticated
api_router.include_router(health_router)

from app.api.v1.documents import router as documents_router
from app.api.v1.extractions import router as extractions_router
from app.api.v1.review import router as review_router
from app.api.v1.audit import router as audit_router

api_router.include_router(documents_router)
api_router.include_router(extractions_router)
api_router.include_router(review_router)
api_router.include_router(audit_router)
