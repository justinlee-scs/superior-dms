from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.repositories.access import (
    get_role_permissions,
    get_user_overrides,
)


def resolve_permissions(db: Session, user: User) -> set[str]:
    permissions = get_role_permissions(db, user)
    overrides = get_user_overrides(db, user)

    for key, effect in overrides.items():
        if effect not in ("ALLOW", "DENY"):
            continue
        if effect == "DENY":
            permissions.discard(key)
        elif effect == "ALLOW":
            permissions.add(key)

    return permissions
