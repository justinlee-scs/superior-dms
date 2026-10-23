from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.repositories import documents as repo


class _Tag:
    def __init__(self, id, name, kind="label"):
        self.id, self.name, self.kind = id, name, kind


class _Document:
    def __init__(self, tags=None):
        self.tags = list(tags or [])


class _DB:
    def __init__(self, document=None, tags=None):
        self.document = document
        self.tags = {tag.id: tag for tag in (tags or [])}
        self.commits = 0

    def get(self, model, key):
        return self.document if model is repo.Document else self.tags.get(key)

    def commit(self):
        self.commits += 1


def test_add_remove_and_set_type_validate_catalog_entries(monkeypatch):
    monkeypatch.setattr(repo, "Document", object)
    monkeypatch.setattr(repo, "TagCatalog", type("TagCatalog", (), {}))
    document_id, label_id, type_id, wrong_id = (uuid4() for _ in range(4))
    label = _Tag(label_id, "invoice")
    doc_type = _Tag(type_id, "invoice", "document_type")
    wrong_kind = _Tag(wrong_id, "wrong")
    document = _Document()
    db = _DB(document, [label, doc_type, wrong_kind])

    assert repo.add_tag(db, document_id, label_id) == ["invoice"]
    assert repo.add_tag(db, document_id, label_id) == ["invoice"]
    assert repo.remove_tag(db, document_id, label_id) == []
    with pytest.raises(ValueError, match="kind='label'"):
        repo.add_tag(db, document_id, type_id)
    with pytest.raises(ValueError, match="kind='label'"):
        repo.remove_tag(db, document_id, uuid4())
    assert db.commits == 3

    # set_document_type uses get() for the actual mapped Document/TagCatalog classes.
    # Exercise its validation independently with model sentinels.
    class DocumentSentinel: pass
    class TagSentinel: pass
    monkeypatch.setattr(repo, "Document", DocumentSentinel)
    monkeypatch.setattr(repo, "TagCatalog", TagSentinel)
    class TypeDB:
        def get(self, model, key):
            return document if model is DocumentSentinel else doc_type if key == type_id else wrong_kind
        def commit(self): pass
        def refresh(self, value): pass
    typed = TypeDB()
    assert repo.set_document_type(typed, document_id, type_id) is document
    assert document.document_type_tag is doc_type
    with pytest.raises(ValueError, match="kind='document_type'"):
        repo.set_document_type(typed, document_id, wrong_id)

def test_document_tag_operations_fail_for_missing_document(monkeypatch):
    monkeypatch.setattr(repo, "Document", object)
    monkeypatch.setattr(repo, "TagCatalog", object)
    db = _DB(None)
    with pytest.raises(ValueError, match="Document not found"):
        repo.add_tag(db, uuid4(), uuid4())
