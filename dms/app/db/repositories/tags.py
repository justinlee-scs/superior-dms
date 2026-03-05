from sqlalchemy.orm import Session

from app.db.models.tag_catalog import TagCatalog
from app.services.extraction.tags import normalize_tag


def list_tag_pool(db: Session, *, query: str | None = None) -> list[str]:
    """Return tag pool.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        query (type=str | None, default=None): Optional search/filter text used to narrow results.
    """
    q = db.query(TagCatalog)
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

    existing = db.query(TagCatalog).filter(TagCatalog.name == normalized).one_or_none()
    if existing:
        return existing.name

    row = TagCatalog(name=normalized)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.name
