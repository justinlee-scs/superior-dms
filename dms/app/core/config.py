import os
from pathlib import Path
from dataclasses import dataclass


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    google_oidc_enabled: bool
    google_oidc_client_id: str
    google_oidc_client_secret: str
    google_oidc_redirect_uri: str
    google_oidc_hosted_domain: str
    google_oidc_post_login_redirect: str


def _build_settings() -> Settings:
    _load_dotenv_file(Path.cwd() / ".env")
    app_env = os.getenv("APP_ENV", "development").strip().lower()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        if app_env == "production":
            raise RuntimeError("DATABASE_URL is required when APP_ENV=production")
        database_url = "postgresql+psycopg://dms_user:dms_password@localhost:5432/dms"

    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        if app_env == "production":
            raise RuntimeError("JWT_SECRET is required when APP_ENV=production")
        jwt_secret = "dev-only-jwt-secret-change-me"

    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip()
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    cors_raw = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    cors_allow_origins = _parse_csv(cors_raw)
    if not cors_allow_origins:
        cors_allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

    cors_allow_credentials = _parse_bool(
        os.getenv("CORS_ALLOW_CREDENTIALS", "true"),
        default=True,
    )

    google_oidc_enabled = _parse_bool(
        os.getenv("GOOGLE_OIDC_ENABLED", "false"),
        default=False,
    )
    google_oidc_client_id = os.getenv("GOOGLE_OIDC_CLIENT_ID", "").strip()
    google_oidc_client_secret = os.getenv("GOOGLE_OIDC_CLIENT_SECRET", "").strip()
    google_oidc_redirect_uri = os.getenv("GOOGLE_OIDC_REDIRECT_URI", "").strip()
    google_oidc_hosted_domain = os.getenv("GOOGLE_OIDC_HOSTED_DOMAIN", "").strip()
    google_oidc_post_login_redirect = os.getenv("GOOGLE_OIDC_POST_LOGIN_REDIRECT", "").strip()

    return Settings(
        app_env=app_env,
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        cors_allow_origins=cors_allow_origins,
        cors_allow_credentials=cors_allow_credentials,
        google_oidc_enabled=google_oidc_enabled,
        google_oidc_client_id=google_oidc_client_id,
        google_oidc_client_secret=google_oidc_client_secret,
        google_oidc_redirect_uri=google_oidc_redirect_uri,
        google_oidc_hosted_domain=google_oidc_hosted_domain,
        google_oidc_post_login_redirect=google_oidc_post_login_redirect,
    )


settings = _build_settings()
