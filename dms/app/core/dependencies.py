from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import get_current_user
from app.services.rbac.permission_checker import require_permission
from app.db.models.user import User


def permission_dependency(permission: str):
    def dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        checker = require_permission(permission)
        checker(db, user)
    return dependency
