from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.rbac import roles as roles_api
from app.schemas.role import RoleCreate, RolePermissionSet, RoleUpdate


class _Query:
    def __init__(self, one_or_none_result=None, all_result=None):
        self._one_or_none_result = one_or_none_result
        self._all_result = all_result or []

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._one_or_none_result

    def all(self):
        return self._all_result


class _DB:
    def __init__(self):
        self.commits = 0
        self.refreshes = []
        self.added = []
        self.get_map = {}
        self.query_map = {}

    def get(self, model, key):
        return self.get_map.get((model, key))

    def query(self, model):
        return self.query_map.get(model, _Query())

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshes.append(obj)


def test_create_role_conflict_and_success() -> None:
    db = _DB()
    payload = RoleCreate(name="editor", description="desc")

    db.query_map[roles_api.Role] = _Query(one_or_none_result=SimpleNamespace(name="editor"))
    with pytest.raises(HTTPException) as exc:
        roles_api.create_role(payload, db=db)
    assert exc.value.status_code == 409

    db_ok = _DB()
    db_ok.query_map[roles_api.Role] = _Query(one_or_none_result=None)
    role = roles_api.create_role(payload, db=db_ok)
    assert role.name == "editor"
    assert db_ok.commits == 1
    assert len(db_ok.added) == 1


def test_update_role_branches() -> None:
    role_id = uuid4()
    role = SimpleNamespace(id=role_id, name="viewer", description=None)
    db = _DB()
    db.get_map[(roles_api.Role, role_id)] = role

    with pytest.raises(HTTPException):
        roles_api.update_role(uuid4(), RoleUpdate(name="x"), db=db)

    with pytest.raises(HTTPException):
        roles_api.update_role(role_id, RoleUpdate(name="   "), db=db)

    db.query_map[roles_api.Role] = _Query(one_or_none_result=SimpleNamespace(id=uuid4(), name="admin"))
    with pytest.raises(HTTPException):
        roles_api.update_role(role_id, RoleUpdate(name="admin"), db=db)

    db.query_map[roles_api.Role] = _Query(one_or_none_result=None)
    updated = roles_api.update_role(role_id, RoleUpdate(name="editor", description="  ok "), db=db)
    assert updated.name == "editor"
    assert updated.description == "ok"


def test_set_role_permissions_empty_missing_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    role_id = uuid4()
    role = SimpleNamespace(id=role_id, permissions=[])

    db = _DB()
    db.get_map[(roles_api.Role, role_id)] = role
    capture = {"set_called": None}
    monkeypatch.setattr(roles_api, "set_permissions", lambda _db, _role, perms: capture.update(set_called=perms))

    empty = roles_api.set_role_permissions(role_id, RolePermissionSet(permission_keys=[]), db=db)
    assert empty == {"status": "ok", "permission_keys": []}
    assert capture["set_called"] == []

    db.query_map[roles_api.Permission] = _Query(all_result=[SimpleNamespace(key="document.read")])
    with pytest.raises(HTTPException):
        roles_api.set_role_permissions(
            role_id,
            RolePermissionSet(permission_keys=["document.read", "document.delete"]),
            db=db,
        )

    perms = [SimpleNamespace(key="document.read"), SimpleNamespace(key="document.upload")]
    db.query_map[roles_api.Permission] = _Query(all_result=perms)
    ok = roles_api.set_role_permissions(
        role_id,
        RolePermissionSet(permission_keys=["document.upload", "document.read"]),
        db=db,
    )
    assert ok == {"status": "ok", "permission_keys": ["document.read", "document.upload"]}


def test_role_managed_users_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    role_id = uuid4()
    user_id = uuid4()
    role = SimpleNamespace(id=role_id, managed_users=[SimpleNamespace(email="b@example.com"), SimpleNamespace(email="a@example.com")])
    user = SimpleNamespace(id=user_id)
    db = _DB()
    db.get_map[(roles_api.Role, role_id)] = role
    db.get_map[(roles_api.User, user_id)] = user

    managed = roles_api.list_managed_users(role_id, db=db)
    assert [u.email for u in managed] == ["a@example.com", "b@example.com"]

    called = {"add": False, "remove": False}
    monkeypatch.setattr(roles_api, "add_managed_user", lambda *_a, **_k: called.__setitem__("add", True))
    monkeypatch.setattr(roles_api, "remove_managed_user", lambda *_a, **_k: called.__setitem__("remove", True))

    assert roles_api.add_role_managed_user(role_id, user_id, db=db) == {"status": "ok"}
    assert roles_api.remove_role_managed_user(role_id, user_id, db=db) == {"status": "ok"}
    assert called["add"] is True
    assert called["remove"] is True


def test_role_hierarchy_and_permission_attach_detach(monkeypatch: pytest.MonkeyPatch) -> None:
    role_id = uuid4()
    src_id = uuid4()
    role = SimpleNamespace(id=role_id, permissions=[SimpleNamespace(key="a")], managed_roles=[])
    src = SimpleNamespace(id=src_id, permissions=[SimpleNamespace(key="b")], managed_roles=[])
    db = _DB()
    db.get_map[(roles_api.Role, role_id)] = role
    db.get_map[(roles_api.Role, src_id)] = src

    monkeypatch.setattr(roles_api, "copy_permissions", lambda *_a, **_k: None)
    assert roles_api.copy_role_permissions(role_id, src_id, db=db)["status"] == "ok"

    db.get_map[(roles_api.Role, role_id)] = SimpleNamespace(id=role_id, managed_roles=[SimpleNamespace(name="viewer"), SimpleNamespace(name="admin")])
    listed = roles_api.list_managed_roles(role_id, db=db)
    assert [r.name for r in listed] == ["admin", "viewer"]

    managed_id = uuid4()
    managed = SimpleNamespace(id=managed_id, name="managed")
    db.get_map[(roles_api.Role, role_id)] = role
    db.get_map[(roles_api.Role, managed_id)] = managed

    monkeypatch.setattr(roles_api, "add_managed_role", lambda *_a, **_k: None)
    monkeypatch.setattr(roles_api, "remove_managed_role", lambda *_a, **_k: None)
    assert roles_api.add_role_hierarchy(role_id, managed_id, db=db) == {"status": "ok"}
    assert roles_api.remove_role_hierarchy(role_id, managed_id, db=db) == {"status": "ok"}

    with pytest.raises(HTTPException):
        roles_api.add_role_hierarchy(role_id, role_id, db=db)

    db.get_map[(roles_api.Role, role_id)] = role
    monkeypatch.setattr(roles_api, "get_permission_by_key", lambda *_a, **_k: SimpleNamespace(key="x"))
    monkeypatch.setattr(roles_api, "attach_permission", lambda *_a, **_k: None)
    monkeypatch.setattr(roles_api, "detach_permission", lambda *_a, **_k: None)
    assert roles_api.add_permission_to_role(role_id, "x", db=db) == {"status": "ok"}
    assert roles_api.remove_permission_from_role(role_id, "x", db=db) == {"status": "ok"}


def test_roles_api_not_found_and_list_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _DB()
    role_id = uuid4()
    src_id = uuid4()
    managed_id = uuid4()
    db.query_map[roles_api.Role] = _Query(all_result=[SimpleNamespace(name="b"), SimpleNamespace(name="a")])
    out = roles_api.list_roles(db=db)
    assert len(out) == 2

    with pytest.raises(HTTPException):
        roles_api.set_role_permissions(role_id, RolePermissionSet(permission_keys=["x"]), db=db)

    with pytest.raises(HTTPException):
        roles_api.copy_role_permissions(role_id, src_id, db=db)

    with pytest.raises(HTTPException):
        roles_api.list_managed_roles(role_id, db=db)

    with pytest.raises(HTTPException):
        roles_api.add_role_hierarchy(role_id, managed_id, db=db)

    with pytest.raises(HTTPException):
        roles_api.remove_role_hierarchy(role_id, managed_id, db=db)

    with pytest.raises(HTTPException):
        roles_api.get_role(role_id, db=db)

    db.get_map[(roles_api.Role, role_id)] = SimpleNamespace(id=role_id, name="viewer", description=None, permissions=[])
    assert roles_api.get_role(role_id, db=db).id == role_id

    monkeypatch.setattr(roles_api, "get_permission_by_key", lambda *_a, **_k: None)
    with pytest.raises(HTTPException):
        roles_api.add_permission_to_role(role_id, "missing", db=db)
    with pytest.raises(HTTPException):
        roles_api.remove_permission_from_role(role_id, "missing", db=db)
