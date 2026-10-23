"""archive + drop: copy every column being retired into _legacy archive
tables (id + the retired columns only), then drop them from the live
documents / document_versions tables. The _legacy tables are intended to
be kept for a period (e.g. a month) after this is deployed and confirmed
working, then dropped in a separate, later migration -- not part of this
one.

Columns retired here:
  documents:          content_hash, document_type (+ enum type)
  document_versions:  classification, confidence, tags (old json),
                       due_date, workflow_notes, ocr_raw_confidence,
                       ocr_engine, ocr_model_version, ocr_latency_ms,
                       ocr_low_confidence, ocr_confidence_lowest,
                       ocr_confidence_average, ocr_processing_log,
                       extraction_jsonb, extraction_raw_jsonb,
                       extraction_corrected_jsonb, layout_json

NOT touched here (deliberately kept live, per decision during this
refactor): document_versions.content (bytea) and storage_bucket /
storage_key / storage_etag / storage_size_bytes -- confirmed mutually
exclusive (62 + 57 = 119 total versions, zero overlap, zero gaps), both
still in active use pending a future consolidation into object storage
only.

Revision ID: 20260925_0023
Revises: 20260925_0022
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "20260925_0023"
down_revision = "20260925_0022"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Archive tables: id + the columns being retired, as they exist
    #    right now. CREATE TABLE ... AS SELECT captures a snapshot.
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            CREATE TABLE documents_legacy AS
            SELECT id, content_hash, document_type::text AS document_type
            FROM documents
            """
        )
    )
    op.create_primary_key("pk_documents_legacy", "documents_legacy", ["id"])

    conn.execute(
        sa.text(
            """
            CREATE TABLE document_versions_legacy AS
            SELECT
                id, classification, confidence, tags, due_date,
                workflow_notes, ocr_raw_confidence, ocr_engine,
                ocr_model_version, ocr_latency_ms, ocr_low_confidence,
                ocr_confidence_lowest, ocr_confidence_average,
                ocr_processing_log, extraction_jsonb,
                extraction_raw_jsonb, extraction_corrected_jsonb,
                layout_json
            FROM document_versions
            """
        )
    )
    op.create_primary_key(
        "pk_document_versions_legacy", "document_versions_legacy", ["id"]
    )

    # ------------------------------------------------------------------
    # 2. Guard: confirm every row was archived before dropping anything.
    #    Raises and rolls back the whole migration if counts don't match
    #    -- alembic runs with transactional DDL, so this is safe.
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            DO $$
            DECLARE
                doc_count int;
                doc_legacy_count int;
                dv_count int;
                dv_legacy_count int;
            BEGIN
                SELECT count(*) INTO doc_count FROM documents;
                SELECT count(*) INTO doc_legacy_count FROM documents_legacy;
                SELECT count(*) INTO dv_count FROM document_versions;
                SELECT count(*) INTO dv_legacy_count FROM document_versions_legacy;

                IF doc_count != doc_legacy_count THEN
                    RAISE EXCEPTION
                        'documents_legacy row count mismatch: % vs %',
                        doc_count, doc_legacy_count;
                END IF;

                IF dv_count != dv_legacy_count THEN
                    RAISE EXCEPTION
                        'document_versions_legacy row count mismatch: % vs %',
                        dv_count, dv_legacy_count;
                END IF;
            END $$;
            """
        )
    )

    # ------------------------------------------------------------------
    # 3. Copy legacy OCR/extraction values into their live replacement
    #    columns before dropping the originals. Keep the compact OCR
    #    measurements and engine details together in ocr_meta.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        UPDATE document_versions
        SET extraction = COALESCE(extraction_corrected_jsonb, extraction, extraction_jsonb),
            extraction_raw = COALESCE(extraction_raw, extraction_raw_jsonb),
            ocr_meta = COALESCE(ocr_meta, '{}'::jsonb)
                || CASE WHEN layout_json IS NULL THEN '{}'::jsonb
                        ELSE jsonb_build_object('layout', layout_json::jsonb) END
                || jsonb_strip_nulls(jsonb_build_object(
                    'confidence', confidence,
                    'raw_confidence', ocr_raw_confidence,
                    'engine', ocr_engine,
                    'model_version', ocr_model_version,
                    'latency_ms', ocr_latency_ms,
                    'low_confidence', ocr_low_confidence,
                    'confidence_lowest', ocr_confidence_lowest,
                    'confidence_average', ocr_confidence_average,
                    'processing_log', ocr_processing_log
                ))
    """))

    # ------------------------------------------------------------------
    # 4. Drop the retired columns from the live tables.
    # ------------------------------------------------------------------
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "document_type")

    for col in (
        "classification",
        "confidence",
        "tags",
        "due_date",
        "workflow_notes",
        "ocr_raw_confidence",
        "ocr_engine",
        "ocr_model_version",
        "ocr_latency_ms",
        "ocr_low_confidence",
        "ocr_confidence_lowest",
        "ocr_confidence_average",
        "ocr_processing_log",
        "extraction_jsonb",
        "extraction_raw_jsonb",
        "extraction_corrected_jsonb",
        "layout_json",
    ):
        op.drop_column("document_versions", col)

    # Enum type is only dropped once nothing references it. document_class
    # and document_class_enum are left alone -- confirmed unused by
    # documents/document_versions in this schema, but not verified against
    # every table, so left untouched rather than assumed dead.
    op.execute("DROP TYPE IF EXISTS document_type_enum")


def downgrade():
    # Re-add the columns, then restore their values from the archive
    # tables. This actually reverses the drop, unlike Phase 2's
    # intentionally no-op downgrade -- here the source data is gone from
    # the live tables, so the archive is the only way back.
    op.execute(
        """
        CREATE TYPE document_type_enum AS ENUM (
            'statement', 'invoice', 'report', 'contract', 'manual',
            'receipt', 'outgoing_invoice', 'incoming_invoice', 'payroll',
            'other', 'document'
        )
        """
    )

    op.add_column(
        "documents",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "document_type",
            sa.Enum(name="document_type_enum", create_type=False),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE documents d
        SET content_hash = dl.content_hash,
            document_type = dl.document_type::document_type_enum
        FROM documents_legacy dl
        WHERE d.id = dl.id
        """
    )

    op.add_column(
        "document_versions", sa.Column("classification", sa.String(), nullable=True)
    )
    op.add_column(
        "document_versions",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "document_versions", sa.Column("due_date", sa.Date(), nullable=True)
    )
    op.add_column(
        "document_versions", sa.Column("workflow_notes", sa.Text(), nullable=True)
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_raw_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_engine", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_model_version", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_latency_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "ocr_low_confidence", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_confidence_lowest", sa.Float(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_confidence_average", sa.Float(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("ocr_processing_log", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("extraction_jsonb", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "extraction_raw_jsonb", sa.dialects.postgresql.JSONB(), nullable=True
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column(
            "extraction_corrected_jsonb", sa.dialects.postgresql.JSONB(), nullable=True
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column("layout_json", sa.JSON(), nullable=True),
    )

    op.execute(
        """
        UPDATE document_versions dv
        SET classification = dvl.classification,
            confidence = dvl.confidence,
            tags = dvl.tags,
            due_date = dvl.due_date,
            workflow_notes = dvl.workflow_notes,
            ocr_raw_confidence = dvl.ocr_raw_confidence,
            ocr_engine = dvl.ocr_engine,
            ocr_model_version = dvl.ocr_model_version,
            ocr_latency_ms = dvl.ocr_latency_ms,
            ocr_low_confidence = dvl.ocr_low_confidence,
            ocr_confidence_lowest = dvl.ocr_confidence_lowest,
            ocr_confidence_average = dvl.ocr_confidence_average,
            ocr_processing_log = dvl.ocr_processing_log,
            extraction_jsonb = dvl.extraction_jsonb,
            extraction_raw_jsonb = dvl.extraction_raw_jsonb,
            extraction_corrected_jsonb = dvl.extraction_corrected_jsonb,
            layout_json = dvl.layout_json
        FROM document_versions_legacy dvl
        WHERE dv.id = dvl.id
        """
    )

    op.drop_table("document_versions_legacy")
    op.drop_table("documents_legacy")