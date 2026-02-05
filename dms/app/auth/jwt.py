from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
