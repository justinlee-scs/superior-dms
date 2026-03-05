from types import SimpleNamespace

import pytest

from app.db.repositories import tags as tags_repo


class _Field:
    def ilike(self, value):
        return ("ilike", value)

    def asc(self):
        return ("asc",)

    def __eq__(self, other):
        return ("eq", other)


class _TagCatalogStub:
    name = _Field()

    def __init__(self, name):
        self.name = name


class _Query:
    def __init__(self, rows=None, one=None):
        self._rows = rows or []
        self._one = one
        self.filtered = None
        self.ordered = False

    def filter(self, criterion):
        self.filtered = criterion
        return self

    def order_by(self, *_args, **_kwargs):
        self.ordered = True
        return self

    def all(self):
        return self._rows

    def one_or_none(self):
        return self._one


class _DB:
    def __init__(self, query_obj):
        self.query_obj = query_obj
        self.added = []
        self.commits = 0
        self.refreshed = []

    def query(self, *_args, **_kwargs):
        return self.query_obj

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_list_tag_pool_orders_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tags_repo, "TagCatalog", _TagCatalogStub)
    rows = [SimpleNamespace(name="invoice"), SimpleNamespace(name="project:alpha")]
    query_obj = _Query(rows=rows)
    db = _DB(query_obj=query_obj)

    tags = tags_repo.list_tag_pool(db=db, query="alpha")

    assert query_obj.filtered == ("ilike", "%alpha%")
    assert query_obj.ordered is True
    assert tags == ["invoice", "project:alpha"]


def test_create_tag_pool_entry_existing_new_and_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tags_repo, "TagCatalog", _TagCatalogStub)

    db_existing = _DB(query_obj=_Query(one=SimpleNamespace(name="project:alpha")))
    assert tags_repo.create_tag_pool_entry(db_existing, tag="Project: Alpha") == "project:alpha"
    assert db_existing.commits == 0
    assert db_existing.added == []

    db_new = _DB(query_obj=_Query(one=None))
    created = tags_repo.create_tag_pool_entry(db_new, tag="Project Beta")
    assert created == "project_beta"
    assert db_new.commits == 1
    assert len(db_new.added) == 1
    assert db_new.added[0].name == "project_beta"
    assert db_new.refreshed == [db_new.added[0]]

    with pytest.raises(ValueError):
        tags_repo.create_tag_pool_entry(db_new, tag="   ")
