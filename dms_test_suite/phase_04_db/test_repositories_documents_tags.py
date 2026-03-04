from types import SimpleNamespace

from app.db.repositories.documents import (
    add_document_version_tags,
    list_existing_tags,
    remove_document_version_tags,
    replace_document_version_tags,
)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.commits = 0
        self.refreshed = []

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.rows)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


def test_list_existing_tags_normalizes_deduplicates_and_sorts() -> None:
    db = _FakeDB(
        rows=[
            (["  Project:Alpha  ", "Invoice", "bad*&tag"],),
            (None,),
            (["invoice", "project:alpha", ""],),
        ]
    )

    tags = list_existing_tags(db)

    assert tags == ["badtag", "invoice", "project:alpha"]


def test_replace_add_remove_document_version_tags() -> None:
    db = _FakeDB()
    version = SimpleNamespace(tags=["invoice"])

    replaced = replace_document_version_tags(db, version, [" Invoice ", "project:Alpha", ""])
    assert replaced == ["invoice", "project:alpha"]

    added = add_document_version_tags(db, version, ["invoice", "payment", "Payment", " "])
    assert added == ["invoice", "payment", "project:alpha"]

    removed = remove_document_version_tags(db, version, ["payment", "does-not-exist"])
    assert removed == ["invoice", "project:alpha"]

    assert db.commits == 3
    assert db.refreshed == [version, version, version]
