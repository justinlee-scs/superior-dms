"""constraints & types: convert timestamp -> timestamptz (confirmed
server timezone is UTC, so this is a straight reinterpretation, not a
shift), json -> jsonb on the columns that survive the Phase 6 drop
(processing_jobs.result, training_feedback_events.predicted_tags /
final_tags -- document_versions.tags and layout_json are NOT converted
here since they're dropped outright in Phase 6, converting them first
would be wasted work), storage_size_bytes -> bigint, and a composite FK
so documents.current_version_id can only point at a version that
actually belongs to that same document.

Revision ID: 20260925_0022
Revises: 20260925_0021
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0022"
down_revision = "20260925_0021"
branch_labels = None
depends_on = None

TIMESTAMPTZ_COLUMNS = [
    ("documents", "created_at"),
    ("document_versions", "created_at"),
    ("ml_classifications", "created_at"),
    ("processing_jobs", "created_at"),
    ("processing_jobs", "updated_at"),
    ("tag_catalog", "created_at"),
    ("training_feedback_events", "created_at"),
]


def upgrade():
    conn = op.get_bind()

    # --- timestamp -> timestamptz ---
    # Server confirmed running in UTC (SHOW timezone -> UTC), so this is
    # a direct reinterpretation of the stored values, not a shift.
    for table, column in TIMESTAMPTZ_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE timestamptz "
            f"USING {column} AT TIME ZONE 'UTC'"
        )

    # --- json -> jsonb, only for columns that survive Phase 6 ---
    op.execute(
        "ALTER TABLE processing_jobs "
        "ALTER COLUMN result TYPE jsonb USING result::jsonb"
    )
    op.execute(
        "ALTER TABLE training_feedback_events "
        "ALTER COLUMN predicted_tags TYPE jsonb USING predicted_tags::jsonb"
    )
    op.execute(
        "ALTER TABLE training_feedback_events "
        "ALTER COLUMN final_tags TYPE jsonb USING final_tags::jsonb"
    )

    # --- storage_size_bytes: integer -> bigint (2GB cap was too low) ---
    op.alter_column(
        "document_versions",
        "storage_size_bytes",
        type_=sa.BigInteger(),
        existing_type=sa.Integer(),
    )

    # --- composite FK: current_version_id must belong to its own document ---
    # Guard check (run manually before applying, not part of the
    # migration itself -- if this returns any rows, VALIDATE CONSTRAINT
    # below will fail and the transaction rolls back cleanly, since
    # alembic runs with transactional DDL):
    #
    #   SELECT d.id FROM documents d
    #   JOIN document_versions dv ON dv.id = d.current_version_id
    #   WHERE dv.document_id <> d.id;
    #
    # Requires a unique constraint on (document_id, id) as the FK target,
    # even though id is already the primary key -- Postgres still
    # requires an explicit unique constraint/index covering exactly the
    # referenced column set for a composite FK.
    op.create_unique_constraint(
        "uq_document_versions_document_id_id",
        "document_versions",
        ["document_id", "id"],
    )
    op.execute(
        "ALTER TABLE documents "
        "ADD CONSTRAINT fk_documents_current_version_document "
        "FOREIGN KEY (id, current_version_id) "
        "REFERENCES document_versions (document_id, id) "
        "NOT VALID"
    )
    op.execute(
        "ALTER TABLE documents "
        "VALIDATE CONSTRAINT fk_documents_current_version_document"
    )
    # NOT VALID + separate VALIDATE avoids a long-held lock scanning the
    # whole table in one step; a NULL current_version_id is exempt from
    # the check under default MATCH SIMPLE semantics.


def downgrade():
    op.drop_constraint(
        "fk_documents_current_version_document",
        "documents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_document_versions_document_id_id",
        "document_versions",
        type_="unique",
    )

    op.alter_column(
        "document_versions",
        "storage_size_bytes",
        type_=sa.Integer(),
        existing_type=sa.BigInteger(),
    )

    op.execute(
        "ALTER TABLE training_feedback_events "
        "ALTER COLUMN final_tags TYPE json USING final_tags::json"
    )
    op.execute(
        "ALTER TABLE training_feedback_events "
        "ALTER COLUMN predicted_tags TYPE json USING predicted_tags::json"
    )
    op.execute(
        "ALTER TABLE processing_jobs "
        "ALTER COLUMN result TYPE json USING result::json"
    )

    for table, column in reversed(TIMESTAMPTZ_COLUMNS):
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE timestamp "
            f"USING {column} AT TIME ZONE 'UTC'"
        )