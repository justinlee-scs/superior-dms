import uuid
from types import SimpleNamespace

from app.db.models.user import User
from app.db.models.role import Role
from app.db.models.user_permission_override import PermissionEffect
from app.db.repositories.users import (
    assign_role,
    clear_permission_overrides,
    remove_role,
    set_permission_override,
    set_permission_overrides,
    set_roles,
)


class _FakeQuery:
    def __init__(self, one_or_none_result=None):
        self._one_or_none_result = one_or_none_result
        self.deleted = False

    def filter_by(self, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._one_or_none_result

    def delete(self, synchronize_session=False):
        self.deleted = True
        self.synchronize_session = synchronize_session


class _FakeDB:
    def __init__(self, one_or_none_result=None):
        self.query_obj = _FakeQuery(one_or_none_result=one_or_none_result)
        self.commits = 0
        self.added = []

    def query(self, *_args, **_kwargs):
        return self.query_obj

    def commit(self):
        self.commits += 1

    def add(self, obj):
        self.added.append(obj)


def test_assign_remove_role_and_set_roles() -> None:
    db = _FakeDB()
    role = SimpleNamespace(id=uuid.uuid4(), name="viewer")
    user = SimpleNamespace(id=uuid.uuid4(), roles=[])

    assign_role(db, user, role)
    assign_role(db, user, role)
    assert user.roles == [role]
    assert db.commits == 1

    remove_role(db, user, role)
    remove_role(db, user, role)
    assert user.roles == []
    assert db.commits == 2

    set_roles(db, user, [role])
    assert user.roles == [role]
    assert db.commits == 3


def test_set_permission_override_updates_existing_row() -> None:
    existing = SimpleNamespace(effect=PermissionEffect.ALLOW)
    db = _FakeDB(one_or_none_result=existing)
    user = SimpleNamespace(id=uuid.uuid4())
    permission = SimpleNamespace(id=uuid.uuid4())

    set_permission_override(db, user, permission, PermissionEffect.DENY)

    assert existing.effect == PermissionEffect.DENY
    assert db.commits == 1
    assert db.added == []


def test_set_permission_override_creates_new_row() -> None:
    db = _FakeDB(one_or_none_result=None)
    user = SimpleNamespace(id=uuid.uuid4())
    permission = SimpleNamespace(id=uuid.uuid4())

    set_permission_override(db, user, permission, PermissionEffect.ALLOW)

    assert len(db.added) == 1
    created = db.added[0]
    assert created.user_id == user.id
    assert created.permission_id == permission.id
    assert created.effect == PermissionEffect.ALLOW
    assert db.commits == 1


def test_bulk_override_helpers_clear_then_write() -> None:
    db = _FakeDB()
    user = SimpleNamespace(id=uuid.uuid4())
    p1 = SimpleNamespace(id=uuid.uuid4())
    p2 = SimpleNamespace(id=uuid.uuid4())

    clear_permission_overrides(db, user)
    assert db.query_obj.deleted is True
    assert db.query_obj.synchronize_session is False
    assert db.commits == 1

    set_permission_overrides(
        db,
        user,
        overrides=[(p1, PermissionEffect.ALLOW), (p2, PermissionEffect.DENY)],
    )
    assert len(db.added) == 2
    assert db.commits == 2


def test_user_model_helpers_has_role_and_repr() -> None:
    user = User(
        email="u@example.com",
        username="u",
        hashed_password="x",
    )
    user.id = uuid.uuid4()
    user.roles.append(Role(name="editor"))

    assert user.has_role("editor") is True
    assert user.has_role("viewer") is False
    assert str(user.id) in repr(user)
