from sqlalchemy.orm import Session
from app.db.models.permission import Permission


def list_permissions(db: Session) -> list[Permission]:
    return db.query(Permission).order_by(Permission.key).all()


def get_permission_by_key(db: Session, key: str) -> Permission | None:
    return db.query(Permission).filter(Permission.key == key).one_or_none()
