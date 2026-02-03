from sqlalchemy.orm import Session
from app.db.models.user import User


def get_role_permissions(db: Session, user: User) -> set[str]:
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.key)
    return perms


def get_user_overrides(db: Session, user: User) -> dict[str, str]:
    return {o.permission.key: o.effect.value for o in user.permission_overrides}
