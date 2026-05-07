from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.db.models.user import User
from app.auth.jwt import verify_password, create_access_token, hash_password
from app.auth.oidc_google import (
    build_google_authorization_url,
    exchange_code_for_id_token,
    fetch_google_identity,
    find_or_create_user_from_google_identity,
    validate_state_token,
)
from app.core.config import settings

from app.auth.deps import get_current_user
from app.services.rbac.access_resolver import resolve_permissions
from app.services.rbac.policy import Permissions

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Define the schema for login request.
    
    Parameters:
        email (type=EmailStr): Parameter.
        password (type=str): Parameter.
    """
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Define the schema for token response.
    
    Parameters:
        access_token (type=str): Parameter.
        token_type (type=str): Parameter.
    """
    access_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    """Define the schema for profile update request.
    
    Parameters:
        username (type=str | None): Parameter.
        current_password (type=str | None): Parameter.
        new_password (type=str | None): Parameter.
    """
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class OIDCLoginStartResponse(BaseModel):
    authorization_url: str


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Handle login.

    Parameters:
        data (type=LoginRequest): Request payload containing client-provided input values.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.get("/me")
def me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handle me.

    Parameters:
        user (type=User, default=Depends(get_current_user)): Authenticated user context for authorization and ownership checks.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    permissions = resolve_permissions(db, user)

    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "roles": [r.name for r in user.roles],
        "permissions": sorted(permissions),
    }


@router.patch("/me/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile.

    Parameters:
        payload (type=ProfileUpdateRequest): Request payload containing client-provided input values.
        user (type=User, default=Depends(get_current_user)): Authenticated user context for authorization and ownership checks.
        db (type=Session, default=Depends(get_db)): Database session used for persistence operations.
    """
    updated = False

    if payload.username is not None:
        username = payload.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        existing = db.query(User).filter(User.username == username, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        user.username = username
        updated = True

    if payload.new_password is not None:
        permissions = resolve_permissions(db, user)
        if Permissions.USER_PASSWORD_SET_SELF not in permissions:
            raise HTTPException(status_code=403, detail="Permission denied")
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

        # Google-first accounts can set a local password without providing a current password.
        if user.auth_provider != "google":
            if not payload.current_password:
                raise HTTPException(status_code=400, detail="Current password is required")
            if not verify_password(payload.current_password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Current password is incorrect")

        user.hashed_password = hash_password(payload.new_password)
        if user.auth_provider == "google":
            user.auth_provider = "local"
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="No profile changes provided")

    db.commit()
    db.refresh(user)

    permissions = resolve_permissions(db, user)
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "roles": [r.name for r in user.roles],
        "permissions": sorted(permissions),
    }


@router.get("/oidc/google/login", response_model=OIDCLoginStartResponse)
def google_oidc_login(post_login_redirect: str | None = Query(default=None)):
    try:
        authorization_url = build_google_authorization_url(post_login_redirect=post_login_redirect)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"authorization_url": authorization_url}


@router.get("/oidc/google/callback")
def google_oidc_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Google auth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    try:
        state_payload = validate_state_token(state)
        id_token = exchange_code_for_id_token(code)
        identity = fetch_google_identity(id_token)
        user = find_or_create_user_from_google_identity(db, identity)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Google OIDC login failed: {exc}") from exc

    token = create_access_token(user.id)

    post_login_redirect = state_payload.get("plr") or settings.google_oidc_post_login_redirect
    if post_login_redirect:
        query = urlencode({"access_token": token, "token_type": "bearer"})
        return RedirectResponse(url=f"{post_login_redirect}?{query}", status_code=302)

    permissions = resolve_permissions(db, user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "roles": [r.name for r in user.roles],
            "permissions": sorted(permissions),
        },
    }
