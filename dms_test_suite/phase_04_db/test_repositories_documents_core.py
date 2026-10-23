from app.db.base import Base
from app.db.models import Document, DocumentVersion, TagCatalog
from app.db.models.documents import document_tags


def test_refactored_tables_match_current_storage_contract():
    assert {"documents", "document_versions", "document_tags", "tag_catalog"} <= set(Base.metadata.tables)

    documents = Document.__table__.columns
    versions = DocumentVersion.__table__.columns
    catalog = TagCatalog.__table__.columns
    assert {"document_type_tag_id", "data", "due_date", "workflow_notes"} <= set(documents.keys())
    assert not {"document_type", "content_hash"} & set(documents.keys())
    assert {"kind", "content_hash", "extraction", "extraction_raw", "ocr_meta"} <= set(versions.keys())
    assert not {"classification", "confidence", "tags", "due_date", "workflow_notes", "ocr_engine", "extraction_jsonb"} & set(versions.keys())
    assert {"name", "kind"} <= set(catalog.keys())
    assert {"document_id", "tag_id", "created_at"} <= set(document_tags.columns.keys())


def test_document_type_and_label_views_derive_from_catalog():
    doc = Document(id=None, filename="sample.pdf")
    doc.document_type_tag = TagCatalog(id=None, name="invoice", kind="document_type")
    doc.tags = [
        TagCatalog(id=None, name="invoice", kind="label"),
        TagCatalog(id=None, name="document", kind="document_type"),
    ]
    assert doc.document_type == "invoice"
    assert doc.label_tags == ["invoice"]
