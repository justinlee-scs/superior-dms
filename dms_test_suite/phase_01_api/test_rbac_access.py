from types import SimpleNamespace

from app.api.v1.rbac.access import get_my_access


def test_get_my_access_returns_sorted_permissions(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.rbac.access.resolve_permissions",
        lambda *_args, **_kwargs: {"documents.read", "documents.upload"},
    )
    user = SimpleNamespace(
        id="u-1",
        email="user@example.com",
        roles=[SimpleNamespace(id="r-2", name="editor"), SimpleNamespace(id="r-1", name="viewer")],
    )

    result = get_my_access(db=object(), current_user=user)

    assert result["user"]["email"] == "user@example.com"
    assert result["permissions"] == ["documents.read", "documents.upload"]
    assert len(result["roles"]) == 2
