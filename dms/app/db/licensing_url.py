from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

DEFAULT_LICENSING_DATABASE_URL = (
    "postgresql+psycopg://dms_user:psqladminpass@127.0.0.1:5432/licensing_db"
)


def _running_inside_container() -> bool:
    return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")


def _rewrite_docker_host_to_localhost(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.hostname != "db" or _running_inside_container():
        return url

    netloc = ""
    if parsed.username:
        netloc = parsed.username
        if parsed.password:
            netloc += f":{parsed.password}"
        netloc += "@"

    netloc += "127.0.0.1"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def get_licensing_database_url() -> str:
    url = os.getenv("LICENSING_DATABASE_URL")
    if not url:
        return DEFAULT_LICENSING_DATABASE_URL
    return _rewrite_docker_host_to_localhost(url)
