from sqlalchemy.orm import Session
from app.db.models.permission import Permission


def list_permissions(db: Session) -> list[Permission]:
    """Return permissions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
    """
    return db.query(Permission).order_by(Permission.key).all()


def get_permission_by_key(db: Session, key: str) -> Permission | None:
    """Return permission by key.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        key (type=str): Function argument used by this operation.
    """
    return db.query(Permission).filter(Permission.key == key).one_or_none()
