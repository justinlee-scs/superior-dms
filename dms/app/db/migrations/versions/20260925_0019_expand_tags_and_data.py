"""expand: tag_catalog constraints, document_tags junction, documents.data jsonb,
document_type_tag_id FK, and document_versions extraction columns

Phase 1 of the schema refactor — purely additive. No existing column is
altered or dropped, and no existing data is modified. Safe to run against
production with no application downtime; the app does not read or write
any of these new columns/tables until the Phase 3 app deploy.

Revision ID: 20260925_0019
Revises: 20260826_0018
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260925_0019"
down_revision = "20260826_0018"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------
    # tag_catalog: enforce unique names, add a kind discriminator so
    # document-type tags can be distinguished from plain label tags.
    # Confirmed via dms_scratch check: zero duplicate names exist today,
    # so this constraint is safe to add with no cleanup.
    # ------------------------------------------------------------------
    op.add_column(
        "tag_catalog",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="label",
        ),
    )
    op.create_check_constraint(
        "ck_tag_catalog_kind",
        "tag_catalog",
        "kind IN ('label', 'document_type')",
    )
    op.create_unique_constraint(
        "uq_tag_catalog_name",
        "tag_catalog",
        ["name"],
    )

    # ------------------------------------------------------------------
    # document_tags: many-to-many junction between documents and
    # tag_catalog. ON DELETE CASCADE on both sides is what gives us the
    # "deleting a tag removes it from every document" behavior with no
    # custom trigger code.
    # ------------------------------------------------------------------
    op.create_table(
        "document_tags",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tag_catalog.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )
    op.create_index(
        "ix_document_tags_tag_id", "document_tags", ["tag_id"]
    )

    # ------------------------------------------------------------------
    # documents: single document-type FK (replaces the document_type
    # enum and document_versions.classification — those are dropped in
    # Phase 5, not here), and the jsonb field store for extracted values.
    # Confirmed via dms_scratch check: zero orphaned uploaded_by_user_id
    # rows, so that FK is also safe to add here even though it's
    # unrelated to tags — small enough to bundle into the expand phase.
    # ------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "document_type_tag_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_documents_document_type_tag_id",
        "documents",
        "tag_catalog",
        ["document_type_tag_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "documents",
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_foreign_key(
        "fk_documents_uploaded_by_user_id",
        "documents",
        "users",
        ["uploaded_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # GIN index for containment queries on documents.data, e.g.
    #   WHERE data @> '{"document_type": "invoice"}'
    # Built CONCURRENTLY so it doesn't lock documents during creation.
    # Must run outside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_documents_data "
            "ON documents USING gin (data jsonb_path_ops)"
        )

    # ------------------------------------------------------------------
    # document_versions: new columns to hold the collapsed extraction
    # data (extraction / extraction_raw / ocr_meta), plus kind
    # (original vs annotated) and content_hash moved up from
    # documents. Old *_jsonb / ocr_* columns are left untouched here —
    # they are dropped in Phase 5 only after the backfill (Phase 2) and
    # app cutover (Phase 3) are verified.
    # ------------------------------------------------------------------
    op.add_column(
        "document_versions",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="original",
        ),
    )
    op.create_check_constraint(
        "ck_document_versions_kind",
        "document_versions",
        "kind IN ('original', 'annotated')",
    )

    op.add_column(
        "document_versions",
        sa.Column("content_hash", sa.String(), nullable=True),
    )
    op.create_index("ix_document_versions_content_hash", "document_versions", ["content_hash"])

    op.add_column(
        "document_versions",
        sa.Column(
            "extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "extraction_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "ocr_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )

    # ------------------------------------------------------------------
    # ml_classifications: confirmed via dms_scratch check that this FK
    # is currently missing entirely (only a PK exists) and zero
    # orphaned rows, so it's safe to add here.
    # ------------------------------------------------------------------
    op.create_foreign_key(
        "fk_ml_classifications_document_version_id",
        "ml_classifications",
        "document_versions",
        ["document_version_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "fk_ml_classifications_document_version_id",
        "ml_classifications",
        type_="foreignkey",
    )

    op.drop_column("document_versions", "ocr_meta")
    op.drop_column("document_versions", "extraction_raw")
    op.drop_column("document_versions", "extraction")
    op.drop_index("ix_document_versions_content_hash", table_name="document_versions")
    op.drop_column("document_versions", "content_hash")
    op.drop_constraint(
        "ck_document_versions_kind", "document_versions", type_="check"
    )
    op.drop_column("document_versions", "kind")

    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_documents_data")

    op.drop_constraint(
        "fk_documents_uploaded_by_user_id", "documents", type_="foreignkey"
    )
    op.drop_column("documents", "data")
    op.drop_constraint(
        "fk_documents_document_type_tag_id", "documents", type_="foreignkey"
    )
    op.drop_column("documents", "document_type_tag_id")

    op.drop_index("ix_document_tags_tag_id", table_name="document_tags")
    op.drop_table("document_tags")

    op.drop_constraint("uq_tag_catalog_name", "tag_catalog", type_="unique")
    op.drop_constraint("ck_tag_catalog_kind", "tag_catalog", type_="check")
    op.drop_column("tag_catalog", "kind")