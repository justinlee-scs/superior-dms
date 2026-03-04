from types import SimpleNamespace

from app.api.v1.rbac.permissions import get_permissions


def test_get_permissions_returns_repository_values(monkeypatch):
    rows = [SimpleNamespace(key="document.read"), SimpleNamespace(key="document.upload")]
    monkeypatch.setattr("app.api.v1.rbac.permissions.list_permissions", lambda _db: rows)
    assert get_permissions(db=object()) == rows
