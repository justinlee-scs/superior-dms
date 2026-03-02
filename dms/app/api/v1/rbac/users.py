from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import uuid

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.role import Role
from app.db.repositories.users import (
    assign_role,
    remove_role,
    set_permission_override,
    set_roles,
    clear_permission_overrides,
    set_permission_overrides,
)
from app.db.repositories.permissions import get_permission_by_key
from app.db.models.user_permission_override import PermissionEffect
from app.db.models.permission import Permission
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions
from app.services.rbac.access_resolver import resolve_permissions
from app.db.repositories.access import get_role_permissions, get_user_overrides
from app.auth.jwt import hash_password
from app.schemas.user import (
    UserResponse,
    UserCreate,
    UserRoleSet,
    UserOverrideSet,
)

router = APIRouter(
    prefix="/users",
    tags=["rbac"],
    dependencies=[Depends(require_permission(Permissions.ADMIN_USERS))],
)


DEFAULT_UNASSIGNED_ROLE = "unassigned"


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.email.asc()).all()


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="Username already exists")

    default_role = db.query(Role).filter(Role.name == DEFAULT_UNASSIGNED_ROLE).one_or_none()
    if default_role is None:
        default_role = Role(name=DEFAULT_UNASSIGNED_ROLE, description="Default role for new users")
        db.add(default_role)
        db.flush()

    user = User(
        id=uuid.uuid4(),
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=payload.is_active,
    )
    user.roles.append(default_role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/{user_id}/roles/{role_id}")
def add_role(user_id: UUID, role_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    role = db.get(Role, role_id)

    if not user or not role:
        raise HTTPException(404)

    assign_role(db, user, role)
    return {"status": "ok"}


@router.put("/{user_id}/roles")
def set_user_roles(user_id: UUID, payload: UserRoleSet, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    role_ids = list(dict.fromkeys(payload.role_ids))
    if not role_ids:
        set_roles(db, user, [])
        return {"status": "ok", "role_ids": []}

    roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
    found_ids = {role.id for role in roles}
    missing = [str(role_id) for role_id in role_ids if role_id not in found_ids]
    if missing:
        raise HTTPException(400, f"Unknown role ids: {', '.join(missing)}")

    set_roles(db, user, roles)
    return {"status": "ok", "role_ids": [str(role.id) for role in roles]}


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


@router.put("/{user_id}/overrides")
def set_overrides_bulk(
    user_id: UUID,
    payload: UserOverrideSet,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    keys = sorted({item.permission_key for item in payload.overrides})
    permissions = db.query(Permission).filter(Permission.key.in_(keys)).all() if keys else []
    permission_by_key = {perm.key: perm for perm in permissions}
    missing = [key for key in keys if key not in permission_by_key]
    if missing:
        raise HTTPException(400, f"Unknown permission keys: {', '.join(missing)}")

    resolved = [
        (permission_by_key[item.permission_key], item.effect)
        for item in payload.overrides
    ]
    set_permission_overrides(db, user, resolved)
    return {"status": "ok"}


@router.get("/{user_id}/permissions/default")
def get_default_permissions(user_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    defaults = sorted(get_role_permissions(db, user))
    return {"user_id": str(user.id), "permissions": defaults}


@router.get("/{user_id}/permissions")
def get_user_permissions(user_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    defaults = sorted(get_role_permissions(db, user))
    effective = sorted(resolve_permissions(db, user))
    overrides = get_user_overrides(db, user)
    return {
        "user_id": str(user.id),
        "default_permissions": defaults,
        "effective_permissions": effective,
        "overrides": overrides,
    }


@router.post("/{user_id}/permissions/reset-default")
def reset_permissions_to_default(user_id: UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    clear_permission_overrides(db, user)
    defaults = sorted(get_role_permissions(db, user))
    return {"status": "ok", "permissions": defaults}
