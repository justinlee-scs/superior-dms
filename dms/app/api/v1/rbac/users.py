from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.role import Role
from app.db.repositories.users import (
    assign_role,
    remove_role,
    set_permission_override,
)
from app.db.repositories.permissions import get_permission_by_key
from app.db.models.user_permission_override import PermissionEffect

router = APIRouter(prefix="/users", tags=["rbac"])


@router.post("/{user_id}/roles/{role_id}")
def add_role(user_id: UUID, role_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    role = db.get(Role, role_id)

    if not user or not role:
        raise HTTPException(404)

    assign_role(db, user, role)
    return {"status": "ok"}


@router.delete("/{user_id}/roles/{role_id}")
def remove_role_from_user(user_id: UUID, role_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    role = db.get(Role, role_id)

    if not user or not role:
        raise HTTPException(404)

    remove_role(db, user, role)
    return {"status": "ok"}


@router.post("/{user_id}/overrides/{permission_key}")
def set_override(
    user_id: UUID,
    permission_key: str,
    effect: PermissionEffect,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    perm = get_permission_by_key(db, permission_key)

    if not user or not perm:
        raise HTTPException(404)

    set_permission_override(db, user, perm, effect)
    return {"status": "ok"}
