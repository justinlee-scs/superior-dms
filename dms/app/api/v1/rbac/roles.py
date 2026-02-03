from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.db.models.role import Role
from app.db.repositories.roles import attach_permission, detach_permission
from app.db.repositories.permissions import get_permission_by_key
from app.schemas.role import RoleWithPermissions

router = APIRouter(prefix="/roles", tags=["rbac"])


@router.get("/{role_id}", response_model=RoleWithPermissions)
def get_role(role_id: UUID, db: Session = Depends(get_db)):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    return role


@router.post("/{role_id}/permissions/{permission_key}")
def add_permission_to_role(
    role_id: UUID,
    permission_key: str,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    perm = get_permission_by_key(db, permission_key)

    if not role or not perm:
        raise HTTPException(404)

    attach_permission(db, role, perm)
    return {"status": "ok"}


@router.delete("/{role_id}/permissions/{permission_key}")
def remove_permission_from_role(
    role_id: UUID,
    permission_key: str,
    db: Session = Depends(get_db),
):
    role = db.get(Role, role_id)
    perm = get_permission_by_key(db, permission_key)

    if not role or not perm:
        raise HTTPException(404)

    detach_permission(db, role, perm)
    return {"status": "ok"}
