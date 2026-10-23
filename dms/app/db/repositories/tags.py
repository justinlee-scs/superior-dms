from sqlalchemy.orm import Session

from app.db.models.tag_catalog import TagCatalog
from app.db.models.documents import Document
from app.services.extraction.tags import normalize_tag


def list_tag_pool(db: Session, *, query: str | None = None, kind: str = "label") -> list[str]:
    """Return tag pool.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        query (type=str | None, default=None): Optional search/filter text used to narrow results.
    """
    q = db.query(TagCatalog).filter(TagCatalog.kind == kind)
    if kind == "label":
        q = q.filter(
            ~TagCatalog.name.like("due_date:%"),
            ~TagCatalog.name.like("payment_due_date:%"),
        )
    if query:
        like = f"%{query.strip().lower()}%"
        q = q.filter(TagCatalog.name.ilike(like))
    rows = q.order_by(TagCatalog.name.asc()).all()
    return [row.name for row in rows]


def create_tag_pool_entry(db: Session, *, tag: str) -> str:
    """Create tag pool entry.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        tag (type=str): Function argument used by this operation.
    """
    normalized = normalize_tag(tag)
    if not normalized:
        raise ValueError("Tag cannot be empty")
    if normalized.startswith(("due_date:", "payment_due_date:")):
        raise ValueError("Due dates are managed with the document date field, not labels")

    existing = db.query(TagCatalog).filter(TagCatalog.name == normalized).one_or_none()
    if existing:
        return existing.name

    row = TagCatalog(name=normalized, kind="label")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.name


def delete_tag_pool_entry(db: Session, *, tag: str) -> bool:
    """Delete tag pool entry.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        tag (type=str): Tag value to delete.
    """
    normalized = normalize_tag(tag)
    if not normalized:
        return False

    row = db.query(TagCatalog).filter(TagCatalog.name == normalized, TagCatalog.kind == "label").one_or_none()
    if not row:
        return False

    db.delete(row)
    db.commit()
    return True


def list_tag_catalog(db: Session, *, query: str | None = None) -> list[TagCatalog]:
    q = db.query(TagCatalog)
    q = q.filter(
        (TagCatalog.kind != "label")
        | (
            ~TagCatalog.name.like("due_date:%")
            & ~TagCatalog.name.like("payment_due_date:%")
        )
    )
    if query:
        q = q.filter(TagCatalog.name.ilike(f"%{query.strip()}%"))
    return q.order_by(TagCatalog.kind.asc(), TagCatalog.name.asc()).all()


def create_document_type(db: Session, *, name: str) -> TagCatalog:
    normalized = normalize_tag(name)
    if not normalized or ":" in normalized or len(normalized) > 64:
        raise ValueError("Type name must be 1-64 characters and cannot contain ':'")
    existing = db.query(TagCatalog).filter(TagCatalog.name == normalized).one_or_none()
    if existing:
        if existing.kind == "document_type":
            raise ValueError("Document type already exists")
        raise ValueError("A label with that name already exists")
    row = TagCatalog(name=normalized, kind="document_type")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_document_type(db: Session, *, tag_id) -> bool:
    row = db.query(TagCatalog).filter(
        TagCatalog.id == tag_id, TagCatalog.kind == "document_type"
    ).one_or_none()
    if not row:
        return False
    assigned_count = db.query(Document).filter(
        Document.document_type_tag_id == row.id
    ).count()
    if assigned_count:
        raise ValueError("Reassign documents using this type before deleting it")
    db.delete(row)
    db.commit()
    return True
