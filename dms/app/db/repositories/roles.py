from sqlalchemy.orm import Session

from app.db.models.role import Role
from app.db.models.permission import Permission


def attach_permission(db: Session, role: Role, permission: Permission) -> None:
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()


def detach_permission(db: Session, role: Role, permission: Permission) -> None:
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()


def set_permissions(db: Session, role: Role, permissions: list[Permission]) -> None:
    role.permissions = permissions
    db.commit()


def copy_permissions(db: Session, target_role: Role, source_role: Role) -> None:
    target_role.permissions = list(source_role.permissions)
    db.commit()


def add_managed_role(db: Session, manager_role: Role, managed_role: Role) -> None:
    if managed_role not in manager_role.managed_roles:
        manager_role.managed_roles.append(managed_role)
        db.commit()


def remove_managed_role(db: Session, manager_role: Role, managed_role: Role) -> None:
    if managed_role in manager_role.managed_roles:
        manager_role.managed_roles.remove(managed_role)
        db.commit()
