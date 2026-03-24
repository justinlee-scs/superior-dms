from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.rbac import users as users_api
from app.db.models.user_permission_override import PermissionEffect
from app.schemas.user import PermissionOverrideInput, UserCreate, UserOverrideSet, UserRoleSet


class _Field:
    def __eq__(self, other):
        return ("eq", other)

    def in_(self, values):
        return ("in", values)


class _Query:
    def __init__(self, first_result=None, one_or_none_result=None, all_result=None):
        self._first = first_result
        self._one = one_or_none_result
        self._all = all_result or []

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._first

    def one_or_none(self):
        return self._one

    def all(self):
        return self._all


class _DB:
    def __init__(self):
        self.get_map = {}
        self.query_map = {}
        self.added = []
        self.commits = 0
        self.refreshes = []
        self.flushes = 0

    def get(self, model, key):
        return self.get_map.get((model, key))

    def query(self, model):
        value = self.query_map.get(model)
        if isinstance(value, list) and value:
            return value.pop(0)
        return value or _Query()

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshes.append(obj)

    def flush(self):
        self.flushes += 1


def test_create_user_conflict_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = UserCreate(username="u", email="u@example.com", password="password123", is_active=True)

    db_email = _DB()
    db_email.query_map[users_api.User] = [_Query(first_result=SimpleNamespace(id="exists-email"))]
    with pytest.raises(HTTPException):
        users_api.create_user(payload, db=db_email)

    db_username = _DB()
    db_username.query_map[users_api.User] = [_Query(first_result=None), _Query(first_result=SimpleNamespace(id="exists-user"))]
    with pytest.raises(HTTPException):
        users_api.create_user(payload, db=db_username)

    class _Role:
        name = None

        def __init__(self, name, description=None):
            self.id = uuid4()
            self.name = name
            self.description = description

    class _User:
        email = _Field()
        username = _Field()

        def __init__(self, **kwargs):
            self.id = kwargs["id"]
            self.username = kwargs["username"]
            self.email = kwargs["email"]
            self.hashed_password = kwargs["hashed_password"]
            self.is_active = kwargs["is_active"]
            self.roles = []

    db_ok = _DB()
    db_ok.query_map[users_api.User] = [_Query(first_result=None), _Query(first_result=None)]
    db_ok.query_map[users_api.Role] = _Query(one_or_none_result=None)
    monkeypatch.setattr(users_api, "Role", _Role)
    monkeypatch.setattr(users_api, "User", _User)
    monkeypatch.setattr(users_api, "hash_password", lambda _p: "hashed")

    created = users_api.create_user(payload, db=db_ok)
    assert created.email == "u@example.com"
    assert created.roles and created.roles[0].name == users_api.DEFAULT_UNASSIGNED_ROLE
    assert db_ok.flushes == 1
    assert db_ok.commits == 1


def test_user_role_and_override_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    role_id = uuid4()
    user = SimpleNamespace(id=user_id, roles=[])
    role = SimpleNamespace(id=role_id)
    db = _DB()
    db.get_map[(users_api.User, user_id)] = user
    db.get_map[(users_api.Role, role_id)] = role

    monkeypatch.setattr(users_api, "assign_role", lambda *_a, **_k: None)
    monkeypatch.setattr(users_api, "remove_role", lambda *_a, **_k: None)
    assert users_api.add_role(user_id, role_id, db=db) == {"status": "ok"}
    assert users_api.remove_role_from_user(user_id, role_id, db=db) == {"status": "ok"}

    roles = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]
    db.query_map[users_api.Role] = _Query(all_result=roles)
    monkeypatch.setattr(users_api, "set_roles", lambda *_a, **_k: None)
    ok_roles = users_api.set_user_roles(user_id, UserRoleSet(role_ids=[roles[0].id, roles[1].id]), db=db)
    assert ok_roles["status"] == "ok"

    db.query_map[users_api.Role] = _Query(all_result=[roles[0]])
    with pytest.raises(HTTPException):
        users_api.set_user_roles(user_id, UserRoleSet(role_ids=[roles[0].id, roles[1].id]), db=db)

    perm = SimpleNamespace(id=uuid4(), key="document.read")
    monkeypatch.setattr(users_api, "get_permission_by_key", lambda *_a, **_k: perm)
    monkeypatch.setattr(users_api, "set_permission_override", lambda *_a, **_k: None)
    assert users_api.set_override(user_id, "document.read", PermissionEffect.ALLOW, db=db) == {"status": "ok"}

    db.query_map[users_api.Permission] = _Query(all_result=[perm])
    monkeypatch.setattr(users_api, "set_permission_overrides", lambda *_a, **_k: None)
    payload = UserOverrideSet(overrides=[PermissionOverrideInput(permission_key="document.read", effect=PermissionEffect.DENY)])
    assert users_api.set_overrides_bulk(user_id, payload, db=db) == {"status": "ok"}


def test_user_permissions_views_and_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)
    db = _DB()
    db.get_map[(users_api.User, user_id)] = user
    monkeypatch.setattr(users_api, "get_role_permissions", lambda *_a, **_k: {"b", "a"})
    monkeypatch.setattr(users_api, "resolve_permissions", lambda *_a, **_k: {"a", "c"})
    monkeypatch.setattr(users_api, "get_user_overrides", lambda *_a, **_k: {"x": "DENY"})
    monkeypatch.setattr(users_api, "clear_permission_overrides", lambda *_a, **_k: None)

    defaults = users_api.get_default_permissions(user_id, db=db)
    assert defaults == {"user_id": str(user_id), "permissions": ["a", "b"]}

    perms = users_api.get_user_permissions(user_id, db=db)
    assert perms["default_permissions"] == ["a", "b"]
    assert perms["effective_permissions"] == ["a", "c"]
    assert perms["overrides"] == {"x": "DENY"}

    reset = users_api.reset_permissions_to_default(user_id, db=db)
    assert reset == {"status": "ok", "permissions": ["a", "b"]}


def test_users_api_not_found_and_list_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _DB()
    user_id = uuid4()
    role_id = uuid4()
    db.query_map[users_api.User] = _Query(all_result=[SimpleNamespace(email="a"), SimpleNamespace(email="b")])
    listed = users_api.list_users(db=db)
    assert len(listed) == 2

    with pytest.raises(HTTPException):
        users_api.get_user(user_id, db=db)
    db.get_map[(users_api.User, user_id)] = SimpleNamespace(id=user_id, email="ok@example.com")
    assert users_api.get_user(user_id, db=db).email == "ok@example.com"
    db.get_map.pop((users_api.User, user_id))

    with pytest.raises(HTTPException):
        users_api.add_role(user_id, role_id, db=db)

    with pytest.raises(HTTPException):
        users_api.set_user_roles(user_id, UserRoleSet(role_ids=[role_id]), db=db)

    db.get_map[(users_api.User, user_id)] = SimpleNamespace(id=user_id, roles=[])
    monkeypatch.setattr(users_api, "set_roles", lambda *_a, **_k: None)
    empty = users_api.set_user_roles(user_id, UserRoleSet(role_ids=[]), db=db)
    assert empty == {"status": "ok", "role_ids": []}


def test_activate_deactivate_and_management_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _DB()
    user_id = uuid4()
    manager = SimpleNamespace(id=user_id, is_active=False, managed_roles=[], managed_users=[], roles=[])
    role_id = uuid4()
    role = SimpleNamespace(id=role_id, name="manager")
    managed_user_id = uuid4()
    managed_user = SimpleNamespace(id=managed_user_id, email="u@example.com")

    db.get_map[(users_api.User, user_id)] = manager
    db.get_map[(users_api.Role, role_id)] = role
    db.get_map[(users_api.User, managed_user_id)] = managed_user

    activated = users_api.activate_user(user_id, db=db)
    assert activated.is_active is True
    deactivated = users_api.deactivate_user(user_id, db=db)
    assert deactivated.is_active is False

    monkeypatch.setattr(users_api, "add_managed_role", lambda *_a, **_k: None)
    monkeypatch.setattr(users_api, "remove_managed_role", lambda *_a, **_k: None)
    monkeypatch.setattr(users_api, "add_managed_user", lambda *_a, **_k: None)
    monkeypatch.setattr(users_api, "remove_managed_user", lambda *_a, **_k: None)

    assert users_api.add_user_managed_role(user_id, role_id, db=db) == {"status": "ok"}
    assert users_api.remove_user_managed_role(user_id, role_id, db=db) == {"status": "ok"}
    assert users_api.add_user_managed_user(user_id, managed_user_id, db=db) == {"status": "ok"}
    assert users_api.remove_user_managed_user(user_id, managed_user_id, db=db) == {"status": "ok"}

    manager.managed_roles = [SimpleNamespace(name="alpha"), SimpleNamespace(name="beta")]
    manager.managed_users = [SimpleNamespace(email="b@example.com"), SimpleNamespace(email="a@example.com")]
    roles = users_api.list_user_managed_roles(user_id, db=db)
    users = users_api.list_user_managed_users(user_id, db=db)
    assert [r.name for r in roles] == ["alpha", "beta"]
    assert [u.email for u in users] == ["a@example.com", "b@example.com"]

    assert users_api.remove_role_from_user(user_id, role_id, db=db) == {"status": "ok"}

    monkeypatch.setattr(users_api, "get_permission_by_key", lambda *_a, **_k: None)
    with pytest.raises(HTTPException):
        users_api.set_override(user_id, "x", PermissionEffect.ALLOW, db=db)

    with pytest.raises(HTTPException):
        users_api.set_overrides_bulk(
            uuid4(),
            UserOverrideSet(overrides=[PermissionOverrideInput(permission_key="x", effect=PermissionEffect.ALLOW)]),
            db=db,
        )

    db.query_map[users_api.Permission] = _Query(all_result=[])
    with pytest.raises(HTTPException):
        users_api.set_overrides_bulk(
            user_id,
            UserOverrideSet(overrides=[PermissionOverrideInput(permission_key="x", effect=PermissionEffect.ALLOW)]),
            db=db,
        )

    with pytest.raises(HTTPException):
        users_api.get_default_permissions(uuid4(), db=db)
    with pytest.raises(HTTPException):
        users_api.get_user_permissions(uuid4(), db=db)
    with pytest.raises(HTTPException):
        users_api.reset_permissions_to_default(uuid4(), db=db)
