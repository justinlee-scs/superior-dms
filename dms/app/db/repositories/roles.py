from sqlalchemy.orm import Session

from app.db.models.role import Role
from app.db.models.permission import Permission


def attach_permission(db: Session, role: Role, permission: Permission) -> None:
    role.permissions.append(permission)
    db.commit()


def detach_permission(db: Session, role: Role, permission: Permission) -> None:
    role.permissions.remove(permission)
    db.commit()
