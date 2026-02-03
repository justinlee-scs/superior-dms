from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repositories.permissions import list_permissions
from app.schemas.permission import PermissionResponse

router = APIRouter(prefix="/permissions", tags=["rbac"])


@router.get("/", response_model=list[PermissionResponse])
def get_permissions(db: Session = Depends(get_db)):
    return list_permissions(db)
