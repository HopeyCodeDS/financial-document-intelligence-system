"""
Celery application factory.

Workers are started with:
    celery -A app.tasks.celery_app worker --loglevel=info
"""
from __future__ import annotations

import os

from celery import Celery

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "fdis",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,               # ack after completion, not on receipt
    worker_prefetch_multiplier=1,      # one task at a time per worker
    task_reject_on_worker_lost=True,
    task_soft_time_limit=600,          # 10 min soft limit → SoftTimeLimitExceeded
    task_time_limit=660,               # 11 min hard limit → SIGKILL
    result_expires=86400,              # results expire after 24h
)
