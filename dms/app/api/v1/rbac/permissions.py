from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.permissions import list_permissions
from app.schemas.permission import PermissionResponse
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

router = APIRouter(
    prefix="/permissions",
    tags=["rbac"],
    dependencies=[Depends(require_permission(Permissions.ADMIN_ROLES))],
)


@router.get("/", response_model=list[PermissionResponse])
def get_permissions(db: Session = Depends(get_db)):
    """Return permissions.

    Parameters:
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    return list_permissions(db)
