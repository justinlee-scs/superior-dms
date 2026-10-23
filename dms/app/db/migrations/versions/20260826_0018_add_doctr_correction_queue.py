"""add doctr correction queue and confidence tracking

Revision ID: 20260826_0018
Revises: 20260715_0017
Create Date: 2026-08-25

Scoped deliberately to ONLY the DocTR/correction-queue changes - does not
touch the pre-existing drift (workspace_documents/processing_jobs/
ml_classifications table drops, classification enum cast, unrelated
server_default/index changes) that showed up in the earlier autogenerate
attempt. That drift is a separate, deliberate decision to make later, not
something to bundle in here.
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_0018"
down_revision = "20260715_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- document_versions: confidence + extraction JSONB + log columns ---
    op.add_column("document_versions", sa.Column("ocr_low_confidence", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("document_versions", sa.Column("ocr_confidence_lowest", sa.Float(), nullable=True))
    op.add_column("document_versions", sa.Column("ocr_confidence_average", sa.Float(), nullable=True))
    op.add_column("document_versions", sa.Column("extraction_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("document_versions", sa.Column("extraction_raw_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("document_versions", sa.Column("extraction_corrected_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # Human-readable stage-timing text from ExtractionTimer in
    # doctr_engine.py. Most-recent-run only, not a history table.
    op.add_column("document_versions", sa.Column("ocr_processing_log", sa.Text(), nullable=True))

    # --- correction queue status enum ---
    correction_status = postgresql.ENUM(
        "pending", "in_review", "confirmed", name="correction_status_enum"
    )
    correction_status.create(op.get_bind(), checkfirst=True)

    # Separate reference for use as a column type below, with
    # create_type=False - the type was already created explicitly above.
    # Reusing the same ENUM object inline in create_table() would make
    # SQLAlchemy try to CREATE TYPE a second time, unconditionally
    # (no checkfirst), causing DuplicateObject in the same transaction.
    correction_status_col = postgresql.ENUM(
        "pending", "in_review", "confirmed", name="correction_status_enum",
        create_type=False,
    )

    # --- ocr_correction_queue ---
    op.create_table(
        "ocr_correction_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("status", correction_status_col, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_ocr_correction_queue_status", "ocr_correction_queue", ["status"])
    op.create_index("ix_ocr_correction_queue_document_version_id", "ocr_correction_queue", ["document_version_id"])

    # --- ocr_word_boxes (background data - not directly edited by the UI,
    # which is field-level only; kept to explain *why* a doc was flagged and
    # for future detection/recognition fine-tuning) ---
    op.create_table(
        "ocr_word_boxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=False),  # [x0,y0,x1,y1] normalized 0-1
        sa.Column("text_raw", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )
    op.create_index("ix_ocr_word_boxes_document_version_id", "ocr_word_boxes", ["document_version_id"])
    op.create_index("ix_ocr_word_boxes_confidence", "ocr_word_boxes", ["confidence"])

    # --- extraction_field_corrections (the correction UI writes here) ---
    op.create_table(
        "extraction_field_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("value_raw", sa.Text(), nullable=True),
        sa.Column("value_corrected", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_extraction_field_corrections_document_version_id", "extraction_field_corrections", ["document_version_id"])


def downgrade() -> None:
    op.drop_table("extraction_field_corrections")
    op.drop_index("ix_ocr_word_boxes_confidence", table_name="ocr_word_boxes")
    op.drop_index("ix_ocr_word_boxes_document_version_id", table_name="ocr_word_boxes")
    op.drop_table("ocr_word_boxes")
    op.drop_index("ix_ocr_correction_queue_document_version_id", table_name="ocr_correction_queue")
    op.drop_index("ix_ocr_correction_queue_status", table_name="ocr_correction_queue")
    op.drop_table("ocr_correction_queue")

    postgresql.ENUM(name="correction_status_enum").drop(op.get_bind(), checkfirst=True)

    op.drop_column("document_versions", "ocr_processing_log")
    op.drop_column("document_versions", "extraction_corrected_jsonb")
    op.drop_column("document_versions", "extraction_raw_jsonb")
    op.drop_column("document_versions", "extraction_jsonb")
    op.drop_column("document_versions", "ocr_confidence_average")
    op.drop_column("document_versions", "ocr_confidence_lowest")
    op.drop_column("document_versions", "ocr_low_confidence")