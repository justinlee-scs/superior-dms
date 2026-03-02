from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.role import Role
from app.db.models.permission import Permission
from app.db.models.user_permission_override import (
    UserPermissionOverride,
    PermissionEffect,
)


def assign_role(db: Session, user: User, role: Role) -> None:
    if role not in user.roles:
        user.roles.append(role)
        db.commit()


def remove_role(db: Session, user: User, role: Role) -> None:
    if role in user.roles:
        user.roles.remove(role)
        db.commit()


def set_permission_override(
    db: Session,
    user: User,
    permission: Permission,
    effect: PermissionEffect,
) -> None:
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
    user.roles = roles
    db.commit()


def clear_permission_overrides(db: Session, user: User) -> None:
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
