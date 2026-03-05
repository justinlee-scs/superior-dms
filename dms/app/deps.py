# app/deps.py

from fastapi import Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.db.models.user import User

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "editor": 2,
    "admin": 3,
}


def require_role(required_role: str):
    """Enforce role.

    Parameters:
        required_role (type=str): Function argument used by this operation.
    """
    if required_role not in ROLE_HIERARCHY:
        raise RuntimeError(f"Unknown required role: {required_role}")

    required_level = ROLE_HIERARCHY[required_role]

    def dependency(user: User = Depends(get_current_user)) -> User:
        """Handle dependency.

        Parameters:
            user (type=User, default=Depends(get_current_user)): Authenticated user context for authorization and ownership checks.
        """
        if not user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no roles assigned",
            )

        user_levels: list[int] = []

        for role in user.roles:
            if role.name not in ROLE_HIERARCHY:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Unknown role assigned to user: {role.name}",
                )
            user_levels.append(ROLE_HIERARCHY[role.name])

        if max(user_levels) < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role ≥ {required_role}",
            )

        return user

    return dependency
