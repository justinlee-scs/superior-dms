from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models.enums import ProcessingStatus
from app.db.repositories import documents as repo


class _Field:
    __hash__ = object.__hash__

    def __eq__(self, other):
        return ("eq", other)

    def in_(self, values):
        return ("in", values)

    def isnot(self, value):
        return ("isnot", value)

    def asc(self):
        return self

    def desc(self):
        return self


class _FakeDocument:
    content_hash = _Field()
    current_version_id = _Field()
    created_at = _Field()

    def __init__(self, id, filename, content_hash):
        self.id = id
        self.filename = filename
        self.content_hash = content_hash
        self.current_version_id = None
        self.document_type = None


class _FakeDocumentVersion:
    document_id = _Field()
    id = _Field()
    created_at = _Field()
    tags = _Field()
    processing_status = _Field()
    classification = _Field()
    confidence = _Field()

    def __init__(self, id, document_id, content, processing_status):
        self.id = id
        self.document_id = document_id
        self.content = content
        self.processing_status = processing_status
        self.extracted_text = None
        self.classification = None
        self.confidence = None
        self.tags = []


class _Query:
    def __init__(self, all_result=None, one_or_none_result=None):
        self._all = all_result or []
        self._one = one_or_none_result

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def outerjoin(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self._one

    def all(self):
        return self._all


class _DB:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshes = []
        self.flushes = 0
        self.get_map = {}
        self.query_map = {}

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        self.refreshes.append(obj)

    def flush(self):
        self.flushes += 1

    def get(self, model, key):
        return self.get_map.get((model, key))

    def query(self, *models):
        key = models[0] if len(models) == 1 else tuple(models)
        return self.query_map.get(key, _Query())


@pytest.fixture
def patched_models(monkeypatch):
    monkeypatch.setattr(repo, "Document", _FakeDocument)
    monkeypatch.setattr(repo, "DocumentVersion", _FakeDocumentVersion)


def test_create_document_and_version_paths(patched_models):
    db = _DB()
    doc = repo.create_document(db, "f.pdf", "hash", commit=True)
    assert doc.filename == "f.pdf"
    assert db.commits == 1

    db2 = _DB()
    existing_doc = _FakeDocument(id=uuid4(), filename="x", content_hash="h")
    db2.get_map[(_FakeDocument, existing_doc.id)] = existing_doc
    ver = repo.create_document_version(db2, existing_doc.id, b"123", set_as_current=True, commit=False)
    assert ver.processing_status == ProcessingStatus.uploaded
    assert existing_doc.current_version_id == ver.id
    assert db2.flushes == 2

    db3 = _DB()
    existing_doc2 = _FakeDocument(id=uuid4(), filename="x", content_hash="h")
    db3.get_map[(_FakeDocument, existing_doc2.id)] = existing_doc2
    ver2 = repo.create_document_version(db3, existing_doc2.id, b"456", set_as_current=True, commit=True)
    assert ver2.processing_status == ProcessingStatus.uploaded
    assert db3.commits == 2
    assert len(db3.refreshes) == 2

    db4 = _DB()
    _ = repo.create_document(db4, "f2.pdf", "hash2", commit=False)
    assert db4.flushes == 1


def test_load_update_and_get_helpers(patched_models):
    db = _DB()
    version_id = uuid4()
    version = _FakeDocumentVersion(id=version_id, document_id=uuid4(), content=b"x", processing_status=ProcessingStatus.pending)
    db.get_map[(_FakeDocumentVersion, version_id)] = version
    assert repo.load_document_version_bytes(db, version_id) == b"x"

    with pytest.raises(ValueError):
        repo.load_document_version_bytes(db, uuid4())

    repo.update_processing_results(
        db,
        version_id,
        extracted_text="text",
        classification="invoice",
        confidence=0.9,
        tags=["invoice"],
        ocr_raw_confidence=0.7,
        ocr_engine="tesseract",
        ocr_model_version="v",
        ocr_latency_ms=12,
    )
    assert version.extracted_text == "text"
    assert version.processing_status == ProcessingStatus.uploaded

    with pytest.raises(ValueError):
        repo.update_processing_results(db, uuid4(), "t", "c", 0.1)

    document_id = uuid4()
    doc = _FakeDocument(id=document_id, filename="f", content_hash="h")
    db.get_map[(_FakeDocument, document_id)] = doc
    assert repo.get_document_by_id(db, document_id) is doc
    assert repo.get_document_version_by_id(db, version_id) is version

    assert repo.get_document_version(db, document_id) is None
    doc.current_version_id = version_id
    assert repo.get_document_version(db, document_id) is version


def test_hash_query_update_type_list_versions_and_delete(patched_models):
    db = _DB()
    doc_id = uuid4()
    v1 = _FakeDocumentVersion(id=uuid4(), document_id=doc_id, content=b"a", processing_status=ProcessingStatus.uploaded)
    v2 = _FakeDocumentVersion(id=uuid4(), document_id=doc_id, content=b"b", processing_status=ProcessingStatus.uploaded)
    doc = _FakeDocument(id=doc_id, filename="f", content_hash="h")

    db.query_map[_FakeDocument] = _Query(one_or_none_result=doc)
    assert repo.get_document_by_hash(db, "h") is doc

    db.get_map[(_FakeDocument, doc_id)] = doc
    updated = repo.update_document_type(db, doc_id, "contract")
    assert updated.document_type == "contract"
    assert db.commits >= 1

    assert repo.update_document_type(db, uuid4(), "x") is None

    db.query_map[_FakeDocumentVersion] = _Query(all_result=[v1, v2])
    assert repo.list_document_versions(db, doc_id) == [v1, v2]

    rows = [(doc, ProcessingStatus.uploaded, "invoice", 0.9, ["invoice"])]
    db.query_map[(
        _FakeDocument,
        _FakeDocumentVersion.processing_status,
        _FakeDocumentVersion.classification,
        _FakeDocumentVersion.confidence,
        _FakeDocumentVersion.tags,
    )] = _Query(all_result=rows)
    db.query_map[(_FakeDocumentVersion.document_id, _FakeDocumentVersion.id)] = _Query(
        all_result=[(doc_id, v1.id), (doc_id, v2.id)]
    )
    doc.current_version_id = v2.id
    listed = repo.list_documents(db)
    assert listed[0][4] == ["invoice"]
    assert listed[0][5] == 2
    assert listed[0][6] == 2

    repo.set_current_document_version(db, doc, v2)
    assert doc.current_version_id == v2.id

    with pytest.raises(ValueError):
        repo.delete_document(db, uuid4())

    db.query_map[_FakeDocumentVersion] = _Query(all_result=[v1, v2])
    repo.delete_document(db, doc_id)
    assert v1 in db.deleted and v2 in db.deleted and doc in db.deleted


def test_list_documents_empty_short_circuit(patched_models):
    db = _DB()
    db.query_map[(_FakeDocument, _FakeDocumentVersion.processing_status, _FakeDocumentVersion.classification, _FakeDocumentVersion.confidence)] = _Query(all_result=[])
    assert repo.list_documents(db) == []
