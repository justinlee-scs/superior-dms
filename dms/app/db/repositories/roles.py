from sqlalchemy.orm import Session

from app.db.models.role import Role
from app.db.models.user import User
from app.db.models.permission import Permission


def attach_permission(db: Session, role: Role, permission: Permission) -> None:
    """Attach permission.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        role (type=Role): Role object(s) used for RBAC assignment or evaluation.
        permission (type=Permission): Permission key(s) used for access-control checks.
    """
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()


def detach_permission(db: Session, role: Role, permission: Permission) -> None:
    """Detach permission.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        role (type=Role): Role object(s) used for RBAC assignment or evaluation.
        permission (type=Permission): Permission key(s) used for access-control checks.
    """
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()


def set_permissions(db: Session, role: Role, permissions: list[Permission]) -> None:
    """Set permissions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        role (type=Role): Role object(s) used for RBAC assignment or evaluation.
        permissions (type=list[Permission]): Permission key(s) used for access-control checks.
    """
    role.permissions = permissions
    db.commit()


def copy_permissions(db: Session, target_role: Role, source_role: Role) -> None:
    """Copy permissions.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        target_role (type=Role): Function argument used by this operation.
        source_role (type=Role): Function argument used by this operation.
    """
    target_role.permissions = list(source_role.permissions)
    db.commit()


def add_managed_role(db: Session, manager_role: Role, managed_role: Role) -> None:
    """Add managed role.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_role (type=Role): Function argument used by this operation.
        managed_role (type=Role): Function argument used by this operation.
    """
    if managed_role not in manager_role.managed_roles:
        manager_role.managed_roles.append(managed_role)
        db.commit()


def remove_managed_role(db: Session, manager_role: Role, managed_role: Role) -> None:
    """Remove managed role.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_role (type=Role): Function argument used by this operation.
        managed_role (type=Role): Function argument used by this operation.
    """
    if managed_role in manager_role.managed_roles:
        manager_role.managed_roles.remove(managed_role)
        db.commit()


def add_managed_user(db: Session, manager_role: Role, managed_user: User) -> None:
    """Add managed user.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_role (type=Role): Function argument used by this operation.
        managed_user (type=User): Function argument used by this operation.
    """
    if managed_user not in manager_role.managed_users:
        manager_role.managed_users.append(managed_user)
        db.commit()


def remove_managed_user(db: Session, manager_role: Role, managed_user: User) -> None:
    """Remove managed user.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_role (type=Role): Function argument used by this operation.
        managed_user (type=User): Function argument used by this operation.
    """
    if managed_user in manager_role.managed_users:
        manager_role.managed_users.remove(managed_user)
        db.commit()
