"""
Celery task: process_document

Enqueued by the upload endpoint. Runs the full pipeline inside a Celery worker
process so CPU-bound OCR/LLM work never blocks the async API event loop.
"""
from __future__ import annotations

import asyncio
import uuid

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="fdis.process_document",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_document(self: object, document_id: str) -> dict:  # type: ignore[misc]
    """
    Entry point for the full document processing pipeline.

    Runs the async orchestrator in a new event loop (Celery workers are sync).
    Returns a summary dict written to the Celery result backend.
    """
    doc_uuid = uuid.UUID(document_id)
    log = logger.bind(document_id=document_id, task_id=getattr(self, "request", {}).get("id"))

    log.info("pipeline_task_started")

    try:
        result = asyncio.run(_run_pipeline(doc_uuid))
        log.info("pipeline_task_completed", status=result.get("status"))
        return result
    except Exception as exc:
        log.exception("pipeline_task_failed", error=str(exc))
        # Celery retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** getattr(self, "request", {}).get("retries", 0) * 30)  # type: ignore[attr-defined]


async def _run_pipeline(document_id: uuid.UUID) -> dict:
    """
    Async wrapper that initialises the DB connection and calls the orchestrator.

    The pipeline orchestrator is imported here (inside the worker process)
    to avoid importing heavy ML libraries in the API process.
    """
    from app.config import get_settings
    from app.db.session import close_db, get_async_session, init_db
    from app.pipeline.orchestrator import PipelineOrchestrator

    settings = get_settings()
    init_db(settings.database_url)

    try:
        async with get_async_session() as session:
            orchestrator = PipelineOrchestrator(session=session, settings=settings)
            context = await orchestrator.run(document_id=document_id)
            return {
                "status": "completed",
                "document_id": str(document_id),
                "final_document_status": context.final_status,
                "risk_level": context.risk_assessment.risk_level.value
                if context.risk_assessment
                else "unknown",
            }
    finally:
        await close_db()
