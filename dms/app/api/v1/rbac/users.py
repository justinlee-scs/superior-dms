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
    add_managed_role,
    remove_managed_role,
    add_managed_user,
    remove_managed_user,
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
from app.schemas.role import RoleResponse

router = APIRouter(
    prefix="/users",
    tags=["rbac"],
    dependencies=[Depends(require_permission(Permissions.ADMIN_USERS))],
)


DEFAULT_UNASSIGNED_ROLE = "unassigned"


@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """Return users.

    Parameters:
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    return db.query(User).order_by(User.email.asc()).all()


@router.get("/{user_id}/managed-roles", response_model=list[RoleResponse])
def list_user_managed_roles(user_id: UUID, db: Session = Depends(get_db)):
    """Return managed roles for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return sorted(user.managed_roles, key=lambda r: r.name)


@router.get("/{user_id}/managed-users", response_model=list[UserResponse])
def list_user_managed_users(user_id: UUID, db: Session = Depends(get_db)):
    """Return managed users for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return sorted(user.managed_users, key=lambda u: u.email)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create user.

    Parameters:
        payload (type=UserCreate): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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


@router.post("/{user_id}/managed-roles/{managed_role_id}")
def add_user_managed_role(user_id: UUID, managed_role_id: UUID, db: Session = Depends(get_db)):
    """Add managed role for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the manager user.
        managed_role_id (type=UUID): Identifier used to locate the role.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    role = db.get(Role, managed_role_id)
    if not user or not role:
        raise HTTPException(404, "User or role not found")

    add_managed_role(db, user, role)
    return {"status": "ok"}


@router.delete("/{user_id}/managed-roles/{managed_role_id}")
def remove_user_managed_role(user_id: UUID, managed_role_id: UUID, db: Session = Depends(get_db)):
    """Remove managed role for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the manager user.
        managed_role_id (type=UUID): Identifier used to locate the role.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    role = db.get(Role, managed_role_id)
    if not user or not role:
        raise HTTPException(404, "User or role not found")

    remove_managed_role(db, user, role)
    return {"status": "ok"}


@router.post("/{user_id}/managed-users/{managed_user_id}")
def add_user_managed_user(user_id: UUID, managed_user_id: UUID, db: Session = Depends(get_db)):
    """Add managed user for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the manager user.
        managed_user_id (type=UUID): Identifier used to locate the managed user.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    managed_user = db.get(User, managed_user_id)
    if not user or not managed_user:
        raise HTTPException(404, "User not found")
    if user.id == managed_user.id:
        raise HTTPException(400, "User cannot manage themselves")

    add_managed_user(db, user, managed_user)
    return {"status": "ok"}


@router.delete("/{user_id}/managed-users/{managed_user_id}")
def remove_user_managed_user(user_id: UUID, managed_user_id: UUID, db: Session = Depends(get_db)):
    """Remove managed user for a user manager.

    Parameters:
        user_id (type=UUID): Identifier used to locate the manager user.
        managed_user_id (type=UUID): Identifier used to locate the managed user.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    managed_user = db.get(User, managed_user_id)
    if not user or not managed_user:
        raise HTTPException(404, "User not found")

    remove_managed_user(db, user, managed_user)
    return {"status": "ok"}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Return user.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: UUID, db: Session = Depends(get_db)):
    """Deactivate user.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: UUID, db: Session = Depends(get_db)):
    """Activate user.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/roles/{role_id}")
def add_role(user_id: UUID, role_id: UUID, db: Session = Depends(get_db)):
    """Add role.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    role = db.get(Role, role_id)

    if not user or not role:
        raise HTTPException(404)

    assign_role(db, user, role)
    return {"status": "ok"}


@router.put("/{user_id}/roles")
def set_user_roles(user_id: UUID, payload: UserRoleSet, db: Session = Depends(get_db)):
    """Set user roles.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        payload (type=UserRoleSet): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Remove role from user.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        role_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Set override.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        permission_key (type=str): Function argument used by this operation.
        effect (type=PermissionEffect): Function argument used by this operation.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Set overrides bulk.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        payload (type=UserOverrideSet): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Return default permissions.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    defaults = sorted(get_role_permissions(db, user))
    return {"user_id": str(user.id), "permissions": defaults}


@router.get("/{user_id}/permissions")
def get_user_permissions(user_id: UUID, db: Session = Depends(get_db)):
    """Return user permissions.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
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
    """Handle reset permissions to default.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    clear_permission_overrides(db, user)
    defaults = sorted(get_role_permissions(db, user))
    return {"status": "ok", "permissions": defaults}
