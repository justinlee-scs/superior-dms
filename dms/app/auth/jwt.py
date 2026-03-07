# app/auth/jwt.py
from datetime import datetime, timedelta
from uuid import UUID
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.jwt_secret
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

# ---- passwords ----

def hash_password(password: str) -> str:
    """Hash password.

    Parameters:
        password (type=str): Function argument used by this operation.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password.

    Parameters:
        plain_password (type=str): Function argument used by this operation.
        hashed_password (type=str): Function argument used by this operation.
    """
    return pwd_context.verify(plain_password, hashed_password)

# ---- tokens ----

def create_access_token(user_id: UUID) -> str:
    """Create access token.

    Parameters:
        user_id (type=UUID): Identifier used to locate the target record.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> UUID:
    """Decode access token.

    Parameters:
        token (type=str): Security token used for authentication/authorization flows.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Missing subject")
    return UUID(sub)
