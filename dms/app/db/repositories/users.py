from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.role import Role
from app.db.models.permission import Permission
from app.db.models.user_permission_override import (
    UserPermissionOverride,
    PermissionEffect,
)


def assign_role(db: Session, user: User, role: Role) -> None:
    """Handle assign role.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
        role (type=Role): Role object(s) used for RBAC assignment or evaluation.
    """
    if role not in user.roles:
        user.roles.append(role)
        db.commit()


def remove_role(db: Session, user: User, role: Role) -> None:
    """Remove role.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
        role (type=Role): Role object(s) used for RBAC assignment or evaluation.
    """
    if role in user.roles:
        user.roles.remove(role)
        db.commit()


def set_permission_override(
    db: Session,
    user: User,
    permission: Permission,
    effect: PermissionEffect,
) -> None:
    """Set permission override.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
        permission (type=Permission): Permission key(s) used for access-control checks.
        effect (type=PermissionEffect): Function argument used by this operation.
    """
    override = (
        db.query(UserPermissionOverride)
        .filter_by(user_id=user.id, permission_id=permission.id)
        .one_or_none()
    )

    if override:
        override.effect = effect
    else:
        override = UserPermissionOverride(
            user_id=user.id,
            permission_id=permission.id,
            effect=effect,
        )
        db.add(override)

    db.commit()


def set_roles(db: Session, user: User, roles: list[Role]) -> None:
    """Set roles.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
        roles (type=list[Role]): Role object(s) used for RBAC assignment or evaluation.
    """
    user.roles = roles
    db.commit()


def clear_permission_overrides(db: Session, user: User) -> None:
    """Clear permission overrides.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
    """
    (
        db.query(UserPermissionOverride)
        .filter(UserPermissionOverride.user_id == user.id)
        .delete(synchronize_session=False)
    )
    db.commit()


def set_permission_overrides(
    db: Session,
    user: User,
    overrides: list[tuple[Permission, PermissionEffect]],
) -> None:
    """Set permission overrides.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        user (type=User): Authenticated user context for authorization and ownership checks.
        overrides (type=list[tuple[Permission, PermissionEffect]]): Function argument used by this operation.
    """
    (
        db.query(UserPermissionOverride)
        .filter(UserPermissionOverride.user_id == user.id)
        .delete(synchronize_session=False)
    )

    for permission, effect in overrides:
        db.add(
            UserPermissionOverride(
                user_id=user.id,
                permission_id=permission.id,
                effect=effect,
            )
        )

    db.commit()


def add_managed_role(db: Session, manager_user: User, managed_role: Role) -> None:
    """Add managed role for a user manager.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_user (type=User): Function argument used by this operation.
        managed_role (type=Role): Function argument used by this operation.
    """
    if managed_role not in manager_user.managed_roles:
        manager_user.managed_roles.append(managed_role)
        db.commit()


def remove_managed_role(db: Session, manager_user: User, managed_role: Role) -> None:
    """Remove managed role for a user manager.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_user (type=User): Function argument used by this operation.
        managed_role (type=Role): Function argument used by this operation.
    """
    if managed_role in manager_user.managed_roles:
        manager_user.managed_roles.remove(managed_role)
        db.commit()


def add_managed_user(db: Session, manager_user: User, managed_user: User) -> None:
    """Add managed user for a user manager.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_user (type=User): Function argument used by this operation.
        managed_user (type=User): Function argument used by this operation.
    """
    if managed_user not in manager_user.managed_users:
        manager_user.managed_users.append(managed_user)
        db.commit()


def remove_managed_user(db: Session, manager_user: User, managed_user: User) -> None:
    """Remove managed user for a user manager.

    Parameters:
        db (type=Session): Database session used for persistence operations.
        manager_user (type=User): Function argument used by this operation.
        managed_user (type=User): Function argument used by this operation.
    """
    if managed_user in manager_user.managed_users:
        manager_user.managed_users.remove(managed_user)
        db.commit()
