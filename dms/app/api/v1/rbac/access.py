from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.security.auth import get_current_user
from app.services.rbac.access_resolver import resolve_permissions
from app.schemas.access import EffectivePermissionsResponse
from app.db.models.user import User

router = APIRouter(prefix="/access", tags=["rbac"])


@router.get("/me", response_model=EffectivePermissionsResponse)
def my_permissions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return {"permissions": resolve_permissions(db, user)}
