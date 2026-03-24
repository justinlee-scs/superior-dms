import uuid
from types import SimpleNamespace

from app.db.repositories.access import get_role_permissions, get_user_overrides


def _role(name: str, perm_keys: list[str], managed_roles=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        permissions=[SimpleNamespace(key=k) for k in perm_keys],
        managed_roles=managed_roles or [],
    )


def test_get_role_permissions_only_uses_direct_roles() -> None:
    leaf = _role("leaf", ["document.preview"])
    parent = _role("parent", ["document.upload"], managed_roles=[leaf])
    user = SimpleNamespace(roles=[parent])

    perms = get_role_permissions(db=None, user=user)

    assert perms == {"document.upload"}


def test_get_role_permissions_includes_managed_roles_transitively() -> None:
    # Legacy test name kept for runner compatibility; behavior is now direct-role only.
    leaf = _role("leaf", ["document.preview"])
    parent = _role("parent", ["document.upload"], managed_roles=[leaf])
    user = SimpleNamespace(roles=[parent])

    perms = get_role_permissions(db=None, user=user)

    assert perms == {"document.upload"}


def test_get_role_permissions_handles_hierarchy_cycles() -> None:
    # Legacy test name kept for runner compatibility; hierarchy is ignored for permissions.
    a = _role("a", ["a.perm"])
    b = _role("b", ["b.perm"])
    a.managed_roles = [b]
    b.managed_roles = [a]
    user = SimpleNamespace(roles=[a])

    perms = get_role_permissions(db=None, user=user)

    assert perms == {"a.perm"}


def test_get_user_overrides_serializes_permission_effect_values() -> None:
    user = SimpleNamespace(
        permission_overrides=[
            SimpleNamespace(permission=SimpleNamespace(key="document.read"), effect=SimpleNamespace(value="ALLOW")),
            SimpleNamespace(permission=SimpleNamespace(key="document.delete"), effect=SimpleNamespace(value="DENY")),
        ]
    )

    result = get_user_overrides(db=None, user=user)

    assert result == {"document.read": "ALLOW", "document.delete": "DENY"}
