from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
MAX_PASSWORD_LENGTH = 72


def _normalize(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string")

    if not password:
        raise ValueError("Password cannot be empty")

    return password


def hash_password(password: str) -> str:
    password = _normalize(password)
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    password = _normalize(password)
    return _pwd_context.verify(password, hashed_password)
