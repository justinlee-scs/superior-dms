from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.db.models.user import User


def require_role(required_role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.name != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {required_role}",
            )
        return user

    return dependency
