from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.db.models.user import User
from app.auth.jwt import verify_password, create_access_token, hash_password

from app.auth.deps import get_current_user
from app.services.rbac.access_resolver import resolve_permissions

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
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
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(payload.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        user.hashed_password = hash_password(payload.new_password)
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
