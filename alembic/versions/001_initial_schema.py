"""Initial schema — all core tables

Revision ID: 001
Revises:
Create Date: 2026-04-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    document_type_enum = postgresql.ENUM(
        "bank_statement", "invoice", "portfolio",
        name="document_type_enum", create_type=False,
    )
    document_status_enum = postgresql.ENUM(
        "uploaded", "processing", "ocr_complete", "masked",
        "extracted", "validated", "reviewed", "failed",
        name="document_status_enum", create_type=False,
    )
    validation_status_enum = postgresql.ENUM(
        "passed", "failed", "partial",
        name="validation_status_enum", create_type=False,
    )
    risk_level_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="risk_level_enum", create_type=False,
    )
    audit_event_category_enum = postgresql.ENUM(
        "pipeline", "security", "review", "system", "api",
        name="audit_event_category_enum", create_type=False,
    )
    audit_event_status_enum = postgresql.ENUM(
        "success", "failure", "warning",
        name="audit_event_status_enum", create_type=False,
    )
    review_priority_enum = postgresql.ENUM(
        "low", "medium", "high", "urgent",
        name="review_priority_enum", create_type=False,
    )
    review_task_status_enum = postgresql.ENUM(
        "pending", "in_review", "approved", "rejected", "escalated",
        name="review_task_status_enum", create_type=False,
    )
    review_decision_type_enum = postgresql.ENUM(
        "approved", "rejected", "escalated", "needs_correction",
        name="review_decision_type_enum", create_type=False,
    )

    for enum in [
        document_type_enum, document_status_enum, validation_status_enum,
        risk_level_enum, audit_event_category_enum, audit_event_status_enum,
        review_priority_enum, review_task_status_enum, review_decision_type_enum,
    ]:
        enum.create(op.get_bind(), checkfirst=True)

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("document_type", sa.Enum(name="document_type_enum"), nullable=False),
        sa.Column("status", sa.Enum(name="document_status_enum"), nullable=False,
                  server_default="uploaded"),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.String(255), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_status", "documents", ["status"])

    # ── extraction_results ────────────────────────────────────────────────────
    op.create_table(
        "extraction_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("extracted_at", sa.String(32), nullable=False),
        sa.Column("raw_llm_response_encrypted", sa.Text(), nullable=True),
        sa.Column("structured_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("confidence_scores", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("overall_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("validation_status", sa.Enum(name="validation_status_enum"), nullable=False),
        sa.Column("validation_violations", postgresql.JSONB(), nullable=False,
                  server_default="[]"),
        sa.Column("risk_level", sa.Enum(name="risk_level_enum"), nullable=False,
                  server_default="low"),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_category", sa.Enum(name="audit_event_category_enum"), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("step_name", sa.String(100), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum(name="audit_event_status_enum"), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("session_id", sa.String(128), nullable=True),
    )
    op.create_index("ix_audit_logs_document_id", "audit_logs", ["document_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor"])

    # Immutability trigger on audit_logs
    op.execute("""
        CREATE TRIGGER trg_audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
    """)

    # ── pii_mappings ──────────────────────────────────────────────────────────
    op.create_table(
        "pii_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("encrypted_mapping", sa.Text(), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", name="uq_pii_mapping_document"),
    )
    op.create_index("ix_pii_mappings_document_id", "pii_mappings", ["document_id"])

    # ── review_tasks ──────────────────────────────────────────────────────────
    op.create_table(
        "review_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_result_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("extraction_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Enum(name="review_priority_enum"), nullable=False,
                  server_default="medium"),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum(name="review_task_status_enum"), nullable=False,
                  server_default="pending"),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("due_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_review_tasks_document_id", "review_tasks", ["document_id"])
    op.create_index("ix_review_tasks_status", "review_tasks", ["status"])

    # ── review_decisions ──────────────────────────────────────────────────────
    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("review_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(255), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("decision", sa.Enum(name="review_decision_type_enum"), nullable=False),
        sa.Column("confidence_override", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("corrections", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_review_decisions_task_id", "review_decisions", ["review_task_id"]
    )


def downgrade() -> None:
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_logs;")

    op.drop_table("review_decisions")
    op.drop_table("review_tasks")
    op.drop_table("pii_mappings")
    op.drop_table("audit_logs")
    op.drop_table("extraction_results")
    op.drop_table("documents")

    for enum_name in [
        "document_type_enum", "document_status_enum", "validation_status_enum",
        "risk_level_enum", "audit_event_category_enum", "audit_event_status_enum",
        "review_priority_enum", "review_task_status_enum", "review_decision_type_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name};")
