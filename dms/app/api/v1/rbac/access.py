from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.services.rbac.access_resolver import resolve_permissions
from app.db.models.user import User

router = APIRouter(prefix="/access", tags=["access"])


@router.get("/me") #is this a duplicate of /me in api/auth.py
def get_my_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permissions = resolve_permissions(db, current_user)

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
        },
        "roles": [
            {"id": str(role.id), "name": role.name}
            for role in current_user.roles
        ],
        "permissions": sorted(list(permissions)),
    }
