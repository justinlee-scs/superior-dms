from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.rbac.access_resolver import resolve_permissions
from app.db.models.user import User


def require_permission(permission: str):
    def checker(db: Session, user: User):
        permissions = resolve_permissions(db, user)
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
    return checker
