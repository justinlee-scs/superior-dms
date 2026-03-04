from sqlalchemy.orm import Session
from app.db.models.user import User


def get_role_permissions(db: Session, user: User) -> set[str]:
    perms: set[str] = set()
    visited_role_ids: set[str] = set()
    stack = list(user.roles)

    # Traverse role hierarchy so manager roles inherit all managed-role permissions.
    while stack:
        role = stack.pop()
        role_id = str(role.id)
        if role_id in visited_role_ids:
            continue
        visited_role_ids.add(role_id)

        for perm in role.permissions:
            perms.add(perm.key)

        for managed_role in role.managed_roles:
            stack.append(managed_role)

    return perms


def get_user_overrides(db: Session, user: User) -> dict[str, str]:
    return {o.permission.key: o.effect.value for o in user.permission_overrides}
