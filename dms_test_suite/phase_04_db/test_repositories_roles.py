from types import SimpleNamespace

from app.db.repositories.roles import (
    add_managed_role,
    add_managed_user,
    attach_permission,
    copy_permissions,
    detach_permission,
    remove_managed_role,
    remove_managed_user,
    set_permissions,
)


class _FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_attach_and_detach_permission_commit_only_on_change() -> None:
    db = _FakeDB()
    perm = SimpleNamespace(key="document.read")
    role = SimpleNamespace(permissions=[])

    attach_permission(db, role, perm)
    attach_permission(db, role, perm)
    assert role.permissions == [perm]
    assert db.commits == 1

    detach_permission(db, role, perm)
    detach_permission(db, role, perm)
    assert role.permissions == []
    assert db.commits == 2


def test_set_permissions_replaces_role_permissions() -> None:
    db = _FakeDB()
    p1 = SimpleNamespace(key="a")
    p2 = SimpleNamespace(key="b")
    role = SimpleNamespace(permissions=[p1])

    set_permissions(db, role, [p2])

    assert role.permissions == [p2]
    assert db.commits == 1


def test_copy_permissions_and_role_hierarchy_mutators() -> None:
    db = _FakeDB()
    source = SimpleNamespace(permissions=[SimpleNamespace(key="x"), SimpleNamespace(key="y")])
    target = SimpleNamespace(permissions=[], managed_roles=[])
    managed = SimpleNamespace(name="viewer")

    copy_permissions(db, target, source)
    add_managed_role(db, target, managed)
    add_managed_role(db, target, managed)
    remove_managed_role(db, target, managed)
    remove_managed_role(db, target, managed)

    assert [p.key for p in target.permissions] == ["x", "y"]
    assert target.managed_roles == []
    assert db.commits == 3


def test_role_managed_users_mutators() -> None:
    db = _FakeDB()
    role = SimpleNamespace(managed_users=[])
    user = SimpleNamespace(email="a@example.com")

    add_managed_user(db, role, user)
    add_managed_user(db, role, user)
    assert role.managed_users == [user]

    remove_managed_user(db, role, user)
    remove_managed_user(db, role, user)
    assert role.managed_users == []
    assert db.commits == 2
