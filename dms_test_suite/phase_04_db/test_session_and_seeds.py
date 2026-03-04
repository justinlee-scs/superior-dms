from types import SimpleNamespace

from app.db.models.permission import Permission
from app.db.seeds.permissions import seed_permissions
from app.db.seeds.roles import ROLE_PERMISSION_MAP, seed_roles
from app.db.session import get_db


class _FakePermissionQuery:
    def __init__(self, permissions):
        self._permissions = permissions
        self._last_key = None

    def all(self):
        return self._permissions

    def filter_by(self, key):
        self._last_key = key
        return self

    def first(self):
        for p in self._permissions:
            if p.key == self._last_key:
                return p
        return None


class _FakeRoleQuery:
    def __init__(self, roles_by_name):
        self._roles_by_name = roles_by_name
        self._last_name = None

    def filter_by(self, name):
        self._last_name = name
        return self

    def first(self):
        return self._roles_by_name.get(self._last_name)


class _FakeSeedDB:
    def __init__(self):
        self.permissions = [
            Permission(key="document.read", description="document.read"),
            Permission(key="document.upload", description="document.upload"),
            Permission(key="document.delete", description="document.delete"),
        ]
        self.roles_by_name = {}
        self.added = []
        self.commits = 0
        self.flushes = 0

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Permission":
            return _FakePermissionQuery(self.permissions)
        if name == "Role":
            return _FakeRoleQuery(self.roles_by_name)
        raise AssertionError(f"Unexpected query model: {name}")

    def add(self, obj):
        self.added.append(obj)
        if hasattr(obj, "name"):
            self.roles_by_name[obj.name] = obj
        if hasattr(obj, "key"):
            self.permissions.append(obj)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1


def test_get_db_yields_session_and_closes_after_use(monkeypatch):
    class _Session:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    created = _Session()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: created)

    generator = get_db()
    yielded = next(generator)
    assert yielded is created

    try:
        next(generator)
    except StopIteration:
        pass

    assert created.closed is True


def test_seed_permissions_adds_missing_and_commits() -> None:
    db = _FakeSeedDB()
    existing_before = {p.key for p in db.permissions}

    seed_permissions(db)

    after = {p.key for p in db.permissions}
    assert existing_before.issubset(after)
    assert db.commits == 1


def test_seed_roles_creates_missing_roles_and_maps_permissions() -> None:
    db = _FakeSeedDB()

    seed_roles(db)

    assert set(ROLE_PERMISSION_MAP.keys()).issubset(set(db.roles_by_name.keys()))
    assert db.commits == 1
    assert db.flushes >= 1
    assert all(hasattr(role, "permissions") for role in db.roles_by_name.values())
