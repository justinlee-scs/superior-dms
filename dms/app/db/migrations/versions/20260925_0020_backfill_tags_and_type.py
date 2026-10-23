"""backfill: populate tag_catalog/document_tags/document_type_tag_id from
document_versions.tags on each document's current version, applying the
agreed cleanup mapping (drop company:*, menu_cnt:*, needs_review,
lilt_company_missing, redundant plain invoice/incoming/outgoing tags;
collapse document_type:document + unknown into one 'unknown' type tag).

Phase 2 of the schema refactor. Every statement is idempotent — safe to
re-run. Nothing is deleted from the OLD columns here; this only copies
forward into the columns Phase 1 added. downgrade() is a no-op by
design, since the source data (document_versions.tags,
documents.document_type) is left completely untouched.

Revision ID: 20260925_0020
Revises: 20260925_0019
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260925_0020"
down_revision = "20260925_0019"
branch_labels = None
depends_on = None


# Tags that map straight into tag_catalog(kind='document_type'), keyed by
# the value after "document_type:".
DOCUMENT_TYPE_MAP = {
    "document": "unknown",
    "unknown": "unknown",
    "invoice": "invoice",
    "statement": "statement",
    "outgoing_invoice": "outgoing_invoice",
    "incoming_invoice": "incoming_invoice",
    "contract": "contract",
    "payroll": "payroll",
    "manual": "manual",
    "receipt": "receipt",
    "other": "other",
    "report": "report",
}

# Plain (non-namespaced) tags that migrate forward as ordinary labels.
#
# NOTE: "receipt" is deliberately excluded here even though it appears as a
# plain tag in document_versions.tags. It also exists as document_type:receipt,
# and tag_catalog.kind is a single column per row -- a tag can't be both a
# document_type and a label at once. Found via dms_scratch dry run: having
# "receipt" in both DOCUMENT_TYPE_MAP and PLAIN_LABEL_TAGS caused this loop
# to run after the document-type loop and silently flip receipt's kind back
# to 'label', which in turn left every document actually classified as a
# receipt unclassified (document_type_tag_id stayed NULL). document_type
# wins for receipt, consistent with it being the intended classification.
PLAIN_LABEL_TAGS = {"banking", "identity", "payment", "legal"}

# Explicitly dropped, not migrated in any form:
#   - company:*            (corrupted — field keys, not values)
#   - menu_cnt:*            (corrupted OCR/table dump)
#   - needs_review          (pipeline state, not a user tag)
#   - lilt_company_missing  (pipeline state, not a user tag)
#   - plain invoice / incoming_invoice / outgoing_invoice
#       (redundant with document_type:* — that becomes the single
#        source of truth via documents.document_type_tag_id)
#   - project:*, security_clearance:*
#       (out of scope for this migration; left in the old tags column)


def upgrade():
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Ensure every needed tag_catalog row exists, with the right kind.
    #
    #    IMPORTANT (found via dms_scratch dry run): tag_catalog already
    #    contained ~115 rows before this migration ever ran, including a
    #    large amount of unrelated corrupted data from a separate bug
    #    elsewhere in the pipeline (raw extracted field dumps such as
    #    menu_cnt:*, menu_price:*, menu_nm:*, total_total_price:*, and
    #    literal namespaced strings like "document_type:invoice" stored
    #    as single tag names, colon included). That cleanup is out of
    #    scope here and left for a later pass.
    #
    #    The canonical clean names this migration needs (invoice,
    #    receipt, contract, incoming_invoice, outgoing_invoice, unknown,
    #    banking, identity, payment, legal) already existed among those
    #    115 rows too, as plain rows with kind left at Phase 1's blanket
    #    default ('label'). ON CONFLICT ... DO UPDATE (not DO NOTHING)
    #    is what corrects kind on those pre-existing rows in place;
    #    DO NOTHING would silently skip them, which is what caused every
    #    document to fail to classify on the first dry run.
    # ------------------------------------------------------------------
    for type_name in set(DOCUMENT_TYPE_MAP.values()):
        conn.execute(
            sa.text(
                """
                INSERT INTO tag_catalog (id, name, kind, created_at)
                VALUES (gen_random_uuid(), :name, 'document_type', now())
                ON CONFLICT (name) DO UPDATE SET kind = 'document_type'
                """
            ),
            {"name": type_name},
        )

    for label in PLAIN_LABEL_TAGS:
        conn.execute(
            sa.text(
                """
                INSERT INTO tag_catalog (id, name, kind, created_at)
                VALUES (gen_random_uuid(), :name, 'label', now())
                ON CONFLICT (name) DO UPDATE SET kind = 'label'
                """
            ),
            {"name": label},
        )

    # Preserve existing values in documents.document_type too. Some records
    # have no document_type:* value in their version tags.
    conn.execute(sa.text("""
        INSERT INTO tag_catalog (id, name, kind, created_at)
        SELECT gen_random_uuid(),
               CASE document_type::text WHEN 'document' THEN 'unknown' ELSE document_type::text END,
               'document_type', now()
        FROM documents
        WHERE document_type IS NOT NULL
        GROUP BY 2
        ON CONFLICT (name) DO UPDATE SET kind = 'document_type'
    """))

    # ------------------------------------------------------------------
    # 2. Resolve, for every document, which version's tags to read:
    #    current_version_id if set, else the highest version_number.
    #    Materialized as a temp table so steps 3-5 all read the same
    #    consistent snapshot.
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            CREATE TEMP TABLE _doc_source_tags AS
            SELECT
                d.id AS document_id,
                COALESCE(cur.tags, latest.tags) AS tags
            FROM documents d
            LEFT JOIN document_versions cur
                ON cur.id = d.current_version_id
            LEFT JOIN LATERAL (
                SELECT dv.tags
                FROM document_versions dv
                WHERE dv.document_id = d.id
                ORDER BY dv.version_number DESC
                LIMIT 1
            ) latest ON d.current_version_id IS NULL
            """
        )
    )

    # ------------------------------------------------------------------
    # 3. documents.document_type_tag_id — from the document_type:* tag,
    #    via DOCUMENT_TYPE_MAP. If a document somehow has more than one
    #    document_type:* tag, the first alphabetically wins (should not
    #    happen in practice, but keeps this deterministic).
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        WITH extracted AS (
            SELECT s.document_id,
                   min(CASE split_part(t, ':', 2)
                       WHEN 'document' THEN 'unknown'
                       ELSE split_part(t, ':', 2) END) AS type_value
            FROM _doc_source_tags s,
                 json_array_elements_text(COALESCE(s.tags, '[]'::json)) AS t
            WHERE t LIKE 'document_type:%'
              AND split_part(t, ':', 2) = ANY(:known_values)
            GROUP BY s.document_id
        ), chosen AS (
            SELECT d.id AS document_id,
                   COALESCE(e.type_value,
                       CASE d.document_type::text
                           WHEN 'document' THEN 'unknown'
                           ELSE d.document_type::text
                       END) AS type_value
            FROM documents d
            LEFT JOIN extracted e ON e.document_id = d.id
        )
        UPDATE documents d
        SET document_type_tag_id = tc.id,
            data = d.data || jsonb_build_object('document_type', tc.name)
        FROM chosen c
        JOIN tag_catalog tc ON tc.kind = 'document_type' AND tc.name = c.type_value
        WHERE d.id = c.document_id AND c.type_value IS NOT NULL
    """), {"known_values": list(DOCUMENT_TYPE_MAP.keys())})

    # ------------------------------------------------------------------
    # 4. document_tags — copy normalized usable labels, including
    #    project/security-clearance tags, while excluding known pipeline
    #    noise and type values that now live in document_type_tag_id.
    # ------------------------------------------------------------------
    conn.execute(sa.text("""
        WITH normalized AS (
            SELECT DISTINCT s.document_id,
                   lower(regexp_replace(btrim(t), '[[:space:]]+', '_', 'g')) AS name
            FROM _doc_source_tags s,
                 json_array_elements_text(COALESCE(s.tags, '[]'::json)) AS t
        ), usable AS (
            SELECT document_id, name
            FROM normalized
            WHERE name <> ''
              AND length(name) <= 80
              AND name NOT LIKE 'document_type:%'
              AND name NOT LIKE 'company:%'
              AND name NOT LIKE 'menu_%'
              AND name NOT LIKE 'total_%'
              AND name NOT LIKE 'due_date:%'
              AND name NOT LIKE 'payment_due_date:%'
              AND name NOT IN (
                  'needs_review', 'lilt_company_missing',
                  'invoice', 'receipt', 'contract', 'incoming_invoice',
                  'outgoing_invoice', 'statement', 'payroll', 'manual',
                  'other', 'report', 'unknown', 'document'
              )
        )
        INSERT INTO tag_catalog (id, name, kind, created_at)
        SELECT gen_random_uuid(), name, 'label', now()
        FROM (SELECT DISTINCT name FROM usable) names
        ON CONFLICT (name) DO UPDATE SET kind = 'label'
    """))

    conn.execute(sa.text("""
        WITH normalized AS (
            SELECT DISTINCT s.document_id,
                   lower(regexp_replace(btrim(t), '[[:space:]]+', '_', 'g')) AS name
            FROM _doc_source_tags s,
                 json_array_elements_text(COALESCE(s.tags, '[]'::json)) AS t
        )
        INSERT INTO document_tags (document_id, tag_id, created_at)
        SELECT n.document_id, tc.id, now()
        FROM normalized n
        JOIN tag_catalog tc ON tc.name = n.name AND tc.kind = 'label'
        WHERE n.name <> ''
          AND length(n.name) <= 80
          AND n.name NOT LIKE 'document_type:%'
          AND n.name NOT LIKE 'company:%'
          AND n.name NOT LIKE 'menu_%'
          AND n.name NOT LIKE 'total_%'
          AND n.name NOT LIKE 'due_date:%'
          AND n.name NOT LIKE 'payment_due_date:%'
          AND n.name NOT IN (
              'needs_review', 'lilt_company_missing',
              'invoice', 'receipt', 'contract', 'incoming_invoice',
              'outgoing_invoice', 'statement', 'payroll', 'manual',
              'other', 'report', 'unknown', 'document'
          )
        ON CONFLICT (document_id, tag_id) DO NOTHING
    """))

    # ------------------------------------------------------------------
    # 5. documents.data — seed with document_type for now (the only
    #    field with real values today; extraction_jsonb/raw/corrected
    #    are confirmed empty across all 119 versions in dms_scratch, so
    #    there is nothing else to backfill into `data` yet). This will
    #    fill out naturally once the DocTR/Ollama pipeline is producing
    #    extraction output and the app starts writing to `data` and
    #    `document_versions.extraction` directly (Phase 3).
    # ------------------------------------------------------------------
    conn.execute(
        sa.text(
            """
            UPDATE documents d
            SET data = data || jsonb_build_object('document_type', tc.name)
            FROM tag_catalog tc
            WHERE d.document_type_tag_id = tc.id
            """
        )
    )

    conn.execute(sa.text("DROP TABLE _doc_source_tags"))


def downgrade():
    # No-op by design. This migration only copies data forward into the
    # columns added by Phase 1 (20260925_0019); the original source
    # columns (document_versions.tags, documents.document_type) are
    # never modified or deleted here. Downgrading Phase 1 (which drops
    # those destination columns/tables entirely) is sufficient to fully
    # undo this migration's effects.
    pass