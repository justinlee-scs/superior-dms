import pytest
from fastapi import HTTPException

from app.services.rbac.access_resolver import resolve_permissions
from app.services.rbac.permission_checker import require_permission
from app.services.rbac.policy import Permissions


def test_resolve_permissions_applies_allow_and_deny_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.rbac.access_resolver.get_role_permissions", lambda *_args, **_kwargs: {"document.read", "document.delete"})
    monkeypatch.setattr(
        "app.services.rbac.access_resolver.get_user_overrides",
        lambda *_args, **_kwargs: {
            "document.delete": "DENY",
            "document.upload": "ALLOW",
            "ignored.permission": "MAYBE",
        },
    )

    result = resolve_permissions(db=object(), user=object())

    assert result == {"document.read", "document.upload"}


def test_require_permission_dependency_allows_and_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    dep = require_permission(Permissions.DOCUMENT_UPLOAD)
    user = object()

    monkeypatch.setattr("app.services.rbac.permission_checker.resolve_permissions", lambda *_args, **_kwargs: {"document.upload"})
    assert dep(db=object(), user=user) is user

    monkeypatch.setattr("app.services.rbac.permission_checker.resolve_permissions", lambda *_args, **_kwargs: {"document.read"})
    with pytest.raises(HTTPException) as exc:
        dep(db=object(), user=user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Permission denied"
