from types import SimpleNamespace

from app.db.repositories.permissions import get_permission_by_key, list_permissions


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._result = None

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._result


class _FakeDB:
    def __init__(self, rows=None, result=None):
        self._query = _FakeQuery(rows or [])
        self._query._result = result

    def query(self, *_args, **_kwargs):
        return self._query


def test_list_permissions_returns_query_results() -> None:
    rows = [SimpleNamespace(key="a"), SimpleNamespace(key="b")]
    db = _FakeDB(rows=rows)
    assert list_permissions(db) == rows


def test_get_permission_by_key_returns_match_or_none() -> None:
    expected = SimpleNamespace(key="document.read")
    db = _FakeDB(result=expected)
    assert get_permission_by_key(db, "document.read") is expected

    db_none = _FakeDB(result=None)
    assert get_permission_by_key(db_none, "missing") is None
