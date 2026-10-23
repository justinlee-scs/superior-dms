"""expand+backfill round 2: documents.due_date / workflow_notes
(moved up from document_versions, confirmed never meaningfully differing
across a document's versions), plus the document_versions.content_hash
backfill that Phase 2 (20260925_0020) omitted -- content_hash moved up to
documents conceptually in the design, but documents.content_hash itself
is not dropped until Phase 6 (archive+drop), so this populates the new
per-version column from the one value the old schema actually recorded
(associated with the document's current version only -- other versions
have no historical hash on record and are correctly left NULL rather
than fabricated).

Revision ID: 20260925_0021
Revises: 20260925_0020
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0021"
down_revision = "20260925_0020"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- expand: new columns on documents ---
    op.add_column("documents", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column(
        "documents", sa.Column("workflow_notes", sa.Text(), nullable=True)
    )

    # --- backfill: due_date / workflow_notes, from current version else
    #     latest version by version_number (same resolution rule used in
    #     Phase 2 for tags, confirmed safe since versions don't disagree) ---
    conn.execute(
        sa.text(
            """
            WITH src AS (
                SELECT
                    d.id AS document_id,
                    COALESCE(cur.due_date, latest.due_date) AS due_date,
                    COALESCE(cur.workflow_notes, latest.workflow_notes)
                        AS workflow_notes
                FROM documents d
                LEFT JOIN document_versions cur
                    ON cur.id = d.current_version_id
                LEFT JOIN LATERAL (
                    SELECT dv.due_date, dv.workflow_notes
                    FROM document_versions dv
                    WHERE dv.document_id = d.id
                    ORDER BY dv.version_number DESC
                    LIMIT 1
                ) latest ON d.current_version_id IS NULL
            )
            UPDATE documents d
            SET due_date = src.due_date,
                workflow_notes = src.workflow_notes
            FROM src
            WHERE d.id = src.document_id
            """
        )
    )

    # --- backfill: document_versions.content_hash, from documents, onto
    #     the current version only (the only version the old schema
    #     actually associated a hash with). Guarded by IS NULL so this is
    #     safe to re-run without clobbering anything already set. ---
    conn.execute(
        sa.text(
            """
            UPDATE document_versions dv
            SET content_hash = d.content_hash
            FROM documents d
            WHERE d.current_version_id = dv.id
              AND dv.content_hash IS NULL
            """
        )
    )


def downgrade():
    # No-op for the backfill (source columns untouched); the new columns
    # themselves are dropped.
    op.drop_column("documents", "workflow_notes")
    op.drop_column("documents", "due_date")