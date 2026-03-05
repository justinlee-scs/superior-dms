from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.services.rbac.access_resolver import resolve_permissions
from app.db.models.user import User


def require_permission(permission: str):
    """Enforce permission.

    Parameters:
        permission (type=str): Permission key(s) used for access-control checks.
    """
    def dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        """Handle dependency.

        Parameters:
            db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
            user (type=User, default=Depends(get_current_user)): Authenticated user context for authorization and ownership checks.
        """
        permissions = resolve_permissions(db, user)
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        return user # Return user for potential further dependencies

    return dependency
