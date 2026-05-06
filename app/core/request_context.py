"""
Request correlation utilities.

A single request (HTTP upload → Celery task → pipeline steps → audit logs) must
be traceable end-to-end via a stable identifier. This module provides:

- An ASGI middleware that assigns or accepts an `X-Request-ID` per request and
  binds it into the structlog context so every log line emitted while handling
  the request includes it.
- Helpers to extract / re-bind the request ID inside a Celery worker so the
  same identifier flows through pipeline logs and audit events.
"""
from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_LOG_KEY = "request_id"
_HEADER_NAME_BYTES = REQUEST_ID_HEADER.lower().encode("latin-1")


def new_request_id() -> str:
    return str(uuid.uuid4())


class RequestIDMiddleware:
    """Pure-ASGI request ID middleware.

    Implemented at the raw ASGI layer rather than via
    ``BaseHTTPMiddleware`` because the latter spawns a child anyio task
    group, which breaks async DB sessions ("Future attached to a different
    loop"). A plain ASGI middleware runs in the same task as the endpoint
    so SQLAlchemy/asyncpg connections work without ceremony.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or mint the request ID.
        incoming: str | None = None
        for name, value in scope.get("headers", []):
            if name == _HEADER_NAME_BYTES:
                incoming = value.decode("latin-1")
                break
        request_id = incoming or new_request_id()

        # Expose to endpoints via request.state.request_id.
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        # Bind to the structlog context so every log line includes it.
        structlog.contextvars.bind_contextvars(**{REQUEST_ID_LOG_KEY: request_id})
        rid_bytes = request_id.encode("latin-1")

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((_HEADER_NAME_BYTES, rid_bytes))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.unbind_contextvars(REQUEST_ID_LOG_KEY)


def bind_request_id(request_id: str | None) -> str:
    """Bind a request ID into the structlog context for the current task.

    If no ID is supplied, a new one is generated so logs always have a value.
    Returns the bound ID for downstream use (audit metadata, etc.).
    """
    rid = request_id or new_request_id()
    structlog.contextvars.bind_contextvars(**{REQUEST_ID_LOG_KEY: rid})
    return rid
