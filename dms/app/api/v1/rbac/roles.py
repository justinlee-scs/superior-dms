from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import uuid

from app.db.session import get_db
from app.db.models.role import Role
from app.db.repositories.roles import (
    attach_permission,
    detach_permission,
    set_permissions,
    copy_permissions,
    add_managed_role,
    remove_managed_role,
)
from app.db.repositories.permissions import get_permission_by_key
from app.db.models.permission import Permission
from app.schemas.role import RoleWithPermissions, RoleResponse, RoleCreate, RolePermissionSet, RoleUpdate
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions

router = APIRouter(
    prefix="/roles",
    tags=["rbac"],
    dependencies=[Depends(require_permission(Permissions.ADMIN_ROLES))],
)


@router.get("/", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    """Return roles.

    Parameters:
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    return db.query(Role).order_by(Role.name.asc()).all()


@router.post("/", response_model=RoleResponse, status_code=201)
def create_role(payload: RoleCreate, db: Session = Depends(get_db)):
    """Create role.

    Parameters:
        payload (type=RoleCreate): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    existing = db.query(Role).filter(Role.name == payload.name).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Role already exists")

    role = Role(id=uuid.uuid4(), name=payload.name, description=payload.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(role_id: UUID, payload: RoleUpdate, db: Session = Depends(get_db)):
    """Update role.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        payload (type=RoleUpdate): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(400, "Role name cannot be empty")
        existing = db.query(Role).filter(Role.name == name, Role.id != role.id).one_or_none()
        if existing:
            raise HTTPException(409, "Role name already exists")
        role.name = name

    if payload.description is not None:
        role.description = payload.description.strip() or None

    db.commit()
    db.refresh(role)
    return role


@router.put("/{role_id}/permissions")
def set_role_permissions(
    role_id: UUID,
    payload: RolePermissionSet,
    db: Session = Depends(get_db),
):
    """Set role permissions.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        payload (type=RolePermissionSet): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")

    requested_keys = sorted(set(payload.permission_keys))
    if not requested_keys:
        set_permissions(db, role, [])
        return {"status": "ok", "permission_keys": []}

    permissions = db.query(Permission).filter(Permission.key.in_(requested_keys)).all()
    found_keys = {p.key for p in permissions}
    missing = [key for key in requested_keys if key not in found_keys]
    if missing:
        raise HTTPException(400, f"Unknown permission keys: {', '.join(missing)}")

    set_permissions(db, role, permissions)
    return {"status": "ok", "permission_keys": sorted(found_keys)}


@router.post("/{role_id}/copy-from/{source_role_id}")
def copy_role_permissions(
    role_id: UUID,
    source_role_id: UUID,
    db: Session = Depends(get_db),
):
    """Copy role permissions.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        source_role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    source_role = db.get(Role, source_role_id)
    if not role or not source_role:
        raise HTTPException(404, "Role not found")

    copy_permissions(db, role, source_role)
    return {"status": "ok", "permission_keys": sorted([p.key for p in role.permissions])}


@router.get("/{role_id}/managed-roles", response_model=list[RoleResponse])
def list_managed_roles(role_id: UUID, db: Session = Depends(get_db)):
    """Return managed roles.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    return sorted(role.managed_roles, key=lambda r: r.name)


@router.post("/{role_id}/managed-roles/{managed_role_id}")
def add_role_hierarchy(role_id: UUID, managed_role_id: UUID, db: Session = Depends(get_db)):
    """Add role hierarchy.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        managed_role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    managed_role = db.get(Role, managed_role_id)
    if not role or not managed_role:
        raise HTTPException(404, "Role not found")
    if role.id == managed_role.id:
        raise HTTPException(400, "Role cannot manage itself")

    add_managed_role(db, role, managed_role)
    return {"status": "ok"}


@router.delete("/{role_id}/managed-roles/{managed_role_id}")
def remove_role_hierarchy(role_id: UUID, managed_role_id: UUID, db: Session = Depends(get_db)):
    """Remove role hierarchy.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        managed_role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    managed_role = db.get(Role, managed_role_id)
    if not role or not managed_role:
        raise HTTPException(404, "Role not found")

    remove_managed_role(db, role, managed_role)
    return {"status": "ok"}


@router.get("/{role_id}", response_model=RoleWithPermissions)
def get_role(role_id: UUID, db: Session = Depends(get_db)):
    """Return role.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Add permission to role.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        permission_key (type=str): Function argument used by this operation.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Remove permission from role.

    Parameters:
        role_id (type=UUID): Identifier used to locate the target record.
        permission_key (type=str): Function argument used by this operation.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    role = db.get(Role, role_id)
    perm = get_permission_by_key(db, permission_key)

    if not role or not perm:
        raise HTTPException(404)

    detach_permission(db, role, perm)
    return {"status": "ok"}
