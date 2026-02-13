from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import get_current_user
from app.services.rbac.access_resolver import resolve_permissions
from app.db.models.user import User


def require_permission(permission: str):
    def dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        permissions = resolve_permissions(db, user)

        print("User:", user.email)
        print("Roles:", [r.name for r in user.roles])
        print("Permissions:", permissions)
        
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        return user # Return user for potential further dependencies

    return dependency
