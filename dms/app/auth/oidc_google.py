from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth.jwt import hash_password
from app.core.config import settings
from app.db.models.role import Role
from app.db.models.user import User

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"

_STATE_TTL_MINUTES = 10


def _ensure_oidc_configured() -> None:
    if not settings.google_oidc_enabled:
        raise ValueError("GOOGLE_OIDC_ENABLED is false")
    required = {
        "GOOGLE_OIDC_CLIENT_ID": settings.google_oidc_client_id,
        "GOOGLE_OIDC_CLIENT_SECRET": settings.google_oidc_client_secret,
        "GOOGLE_OIDC_REDIRECT_URI": settings.google_oidc_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing OIDC settings: {', '.join(missing)}")


def build_google_authorization_url(post_login_redirect: str | None = None) -> str:
    _ensure_oidc_configured()

    state_payload = {
        "nonce": secrets.token_urlsafe(24),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES)).timestamp()),
    }
    if post_login_redirect:
        state_payload["plr"] = post_login_redirect
    state_token = jwt.encode(state_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    params = {
        "client_id": settings.google_oidc_client_id,
        "redirect_uri": settings.google_oidc_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state_token,
    }
    if settings.google_oidc_hosted_domain:
        params["hd"] = settings.google_oidc_hosted_domain

    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_id_token(code: str) -> str:
    _ensure_oidc_configured()

    payload = {
        "code": code,
        "client_id": settings.google_oidc_client_id,
        "client_secret": settings.google_oidc_client_secret,
        "redirect_uri": settings.google_oidc_redirect_uri,
        "grant_type": "authorization_code",
    }

    response = requests.post(GOOGLE_TOKEN_ENDPOINT, data=payload, timeout=20)
    response.raise_for_status()
    token_payload = response.json()

    id_token = token_payload.get("id_token")
    if not id_token:
        raise ValueError("Google token response missing id_token")
    return id_token


def validate_state_token(state_token: str) -> dict:
    try:
        return jwt.decode(state_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired OIDC state") from exc


def fetch_google_identity(id_token: str) -> dict[str, str | bool]:
    response = requests.get(
        GOOGLE_TOKENINFO_ENDPOINT,
        params={"id_token": id_token},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("aud") != settings.google_oidc_client_id:
        raise ValueError("Google token audience mismatch")

    issuer = payload.get("iss")
    if issuer not in {"https://accounts.google.com", "accounts.google.com"}:
        raise ValueError("Invalid Google token issuer")

    email = payload.get("email")
    sub = payload.get("sub")
    if not email or not sub:
        raise ValueError("Google token missing email/sub")

    if settings.google_oidc_hosted_domain:
        if payload.get("hd") != settings.google_oidc_hosted_domain:
            raise ValueError("Google hosted domain mismatch")

    return {
        "sub": sub,
        "email": email,
        "email_verified": str(payload.get("email_verified", "false")).lower() == "true",
        "name": payload.get("name") or "",
    }


def _base_username_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip().lower()
    cleaned = "".join(ch for ch in local if ch.isalnum() or ch in {"_", ".", "-"})
    return cleaned or "user"


def _ensure_unique_username(db: Session, base: str) -> str:
    username = base
    suffix = 1
    while db.query(User).filter(User.username == username).first() is not None:
        username = f"{base}{suffix}"
        suffix += 1
    return username


def _random_unusable_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "oidc-" + "".join(secrets.choice(alphabet) for _ in range(length))


def find_or_create_user_from_google_identity(db: Session, identity: dict[str, str | bool]) -> User:
    oidc_subject = str(identity["sub"])
    email = str(identity["email"]).strip().lower()

    user = db.query(User).filter(User.oidc_subject == oidc_subject).first()
    if user:
        if user.email != email:
            user.email = email
            db.commit()
            db.refresh(user)
        return user

    user = db.query(User).filter(User.email == email).first()
    if user:
        user.oidc_subject = oidc_subject
        # Keep existing auth provider for previously-created local users
        # so dev/admin password login continues to work unchanged.
        if not user.auth_provider:
            user.auth_provider = "local"
        db.commit()
        db.refresh(user)
        return user

    username = _ensure_unique_username(db, _base_username_from_email(email))
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(_random_unusable_password()),
        auth_provider="google",
        oidc_subject=oidc_subject,
        is_active=True,
    )
    db.add(user)
    db.flush()

    default_role = db.query(Role).filter(Role.name == "unassigned").first()
    if default_role is not None:
        user.roles.append(default_role)

    db.commit()
    db.refresh(user)
    return user
