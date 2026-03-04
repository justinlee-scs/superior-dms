from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.deps import require_role


def test_require_role_rejects_unknown_required_role() -> None:
    with pytest.raises(RuntimeError):
        require_role("superadmin")


def test_require_role_rejects_user_without_roles() -> None:
    dep = require_role("viewer")
    user = SimpleNamespace(roles=[])

    with pytest.raises(HTTPException) as exc:
        dep(user=user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "User has no roles assigned"


def test_require_role_rejects_unknown_assigned_role() -> None:
    dep = require_role("viewer")
    user = SimpleNamespace(roles=[SimpleNamespace(name="mystery")])

    with pytest.raises(HTTPException) as exc:
        dep(user=user)
    assert exc.value.status_code == 403
    assert "Unknown role assigned to user" in exc.value.detail


def test_require_role_rejects_insufficient_role_level() -> None:
    dep = require_role("admin")
    user = SimpleNamespace(roles=[SimpleNamespace(name="viewer"), SimpleNamespace(name="editor")])

    with pytest.raises(HTTPException) as exc:
        dep(user=user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Requires role ≥ admin"


def test_require_role_allows_higher_role() -> None:
    dep = require_role("editor")
    user = SimpleNamespace(roles=[SimpleNamespace(name="admin")])

    assert dep(user=user) is user
