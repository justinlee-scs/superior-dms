from types import SimpleNamespace

from app.main import create_tables, health, list_docs, root


class _FakeConn:
    def __init__(self):
        self.calls = 0

    def execute(self, _stmt):
        self.calls += 1


class _FakeBegin:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return _FakeBegin(self.conn)


def test_main_root_health_and_list_docs() -> None:
    assert root() == {"message": "DMS API running"}
    assert health() == {"status": "ok"}
    assert list_docs(user=SimpleNamespace(email="a@b.com")) == {"msg": "Hello a@b.com"}


def test_create_tables_runs_create_all_and_migrations(monkeypatch):
    calls = {"create_all": 0}
    conn = _FakeConn()

    class _Metadata:
        def create_all(self, bind):
            assert bind is not None
            calls["create_all"] += 1

    monkeypatch.setattr("app.main.Base", SimpleNamespace(metadata=_Metadata()))
    monkeypatch.setattr("app.main.engine", _FakeEngine(conn))

    create_tables()

    assert calls["create_all"] == 1
    assert conn.calls == 5
