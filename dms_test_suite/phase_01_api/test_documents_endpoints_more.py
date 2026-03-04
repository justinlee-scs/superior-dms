import asyncio
import io
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.api import documents as docs_api
from app.schemas.documents import DocumentTypeUpdate
from app.schemas.tags import TagUpdateRequest


class _Begin:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DB:
    def __init__(self):
        self.flushes = 0

    def begin(self):
        return _Begin()

    def flush(self):
        self.flushes += 1


def _run(coro):
    return asyncio.run(coro)


class _Upload:
    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


def _upload(name: str, data: bytes) -> _Upload:
    return _Upload(filename=name, data=data)


def _doc(doc_id=None):
    return SimpleNamespace(
        id=doc_id or uuid4(),
        filename="file.pdf",
        created_at=datetime.now(timezone.utc),
        current_version_id=None,
        document_type="incoming_invoice",
        status="uploaded",
        confidence=0.8,
    )


def _version(version_id=None, document_id=None):
    doc = SimpleNamespace(filename="file.pdf", document_type="incoming_invoice")
    return SimpleNamespace(
        id=version_id or uuid4(),
        document_id=document_id or uuid4(),
        document=doc,
        content=b"abc",
        processing_status="uploaded",
        classification="invoice",
        confidence=0.9,
        ocr_engine="tesseract",
        ocr_model_version="pytesseract",
        tags=["invoice"],
        created_at=datetime.now(timezone.utc),
    )


def test_upload_document_empty_and_duplicate(monkeypatch: pytest.MonkeyPatch):
    db = _DB()
    empty = _upload("a.pdf", b"")
    with pytest.raises(HTTPException) as exc:
        _run(docs_api.upload_document(file=empty, db=db))
    assert exc.value.status_code == 400

    monkeypatch.setattr(docs_api, "_validate_supported_upload", lambda *_a, **_k: None)
    monkeypatch.setattr("app.services.hash.compute_content_hash", lambda _b: "hash")
    monkeypatch.setattr(docs_api, "get_document_by_hash", lambda **_k: _doc())
    dup = _upload("a.pdf", b"%PDF-1.7")
    with pytest.raises(HTTPException) as exc2:
        _run(docs_api.upload_document(file=dup, db=db))
    assert exc2.value.status_code == 409


def test_upload_document_success(monkeypatch: pytest.MonkeyPatch):
    db = _DB()
    doc = _doc()
    ver = _version(document_id=doc.id)
    doc.current_version_id = ver.id
    called = {"processed": False}

    monkeypatch.setattr(docs_api, "_validate_supported_upload", lambda *_a, **_k: None)
    monkeypatch.setattr("app.services.hash.compute_content_hash", lambda _b: "hash")
    monkeypatch.setattr(docs_api, "get_document_by_hash", lambda **_k: None)
    monkeypatch.setattr(docs_api, "create_document", lambda **_k: doc)
    monkeypatch.setattr(docs_api, "create_document_version", lambda **_k: ver)
    monkeypatch.setattr(docs_api, "process_document", lambda **_k: called.update(processed=True))

    resp = _run(docs_api.upload_document(file=_upload("a.pdf", b"%PDF-1.7"), db=db))
    assert resp.id == doc.id
    assert called["processed"] is True


def test_get_documents_and_get_document(monkeypatch: pytest.MonkeyPatch):
    d = _doc()
    v1 = _version(document_id=d.id)
    v2 = _version(document_id=d.id)
    v2.id = uuid4()
    d.current_version_id = v2.id
    rows = [(d, "uploaded", "invoice", 0.9, 2, 2)]
    monkeypatch.setattr(docs_api, "list_documents", lambda **_k: rows)
    docs = docs_api.get_documents(db=object())
    assert len(docs) == 1 and docs[0].version_count == 2

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.get_document(d.id, db=object())

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: d)
    monkeypatch.setattr(docs_api, "get_document_version", lambda **_k: v2)
    monkeypatch.setattr(docs_api, "list_document_versions", lambda **_k: [v1, v2])
    out = docs_api.get_document(d.id, db=object())
    assert out.current_version_number == 2


def test_type_output_delete_download_preview(monkeypatch: pytest.MonkeyPatch):
    d = _doc()
    v = _version(document_id=d.id)

    monkeypatch.setattr(docs_api, "update_document_type", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.set_document_type(d.id, DocumentTypeUpdate(document_type="contract"), db=object())
    monkeypatch.setattr(docs_api, "update_document_type", lambda **_k: d)
    assert docs_api.set_document_type(d.id, DocumentTypeUpdate(document_type="contract"), db=object()).id == d.id

    monkeypatch.setattr(docs_api, "get_document_version", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.get_document_output(d.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_version", lambda **_k: v)
    assert docs_api.get_document_output(d.id, db=object()) is v

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.delete_document(d.id, db=object())
    called = {"deleted": False}
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: d)
    monkeypatch.setattr(docs_api, "delete_document_repo", lambda **_k: called.update(deleted=True))
    docs_api.delete_document(d.id, db=object())
    assert called["deleted"] is True

    monkeypatch.setattr(docs_api, "get_document_version", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.download_document(d.id, db=object())
    with pytest.raises(HTTPException):
        docs_api.preview_document(d.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_version", lambda **_k: v)
    dl = docs_api.download_document(d.id, db=object())
    assert isinstance(dl, StreamingResponse)
    pv = docs_api.preview_document(d.id, db=object())
    assert isinstance(pv, StreamingResponse)


def test_versions_create_set_current_download_preview_tags(monkeypatch: pytest.MonkeyPatch):
    db = _DB()
    d = _doc()
    v = _version(document_id=d.id)
    d.current_version_id = v.id

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.get_document_versions(d.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: d)
    monkeypatch.setattr(docs_api, "list_document_versions", lambda **_k: [v])
    versions = docs_api.get_document_versions(d.id, db=object())
    assert versions[0].is_current is True

    empty = _upload("a.pdf", b"")
    with pytest.raises(HTTPException):
        _run(docs_api.create_new_document_version(d.id, file=empty, db=db))

    monkeypatch.setattr(docs_api, "_validate_supported_upload", lambda *_a, **_k: None)
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        _run(docs_api.create_new_document_version(d.id, file=_upload("a.pdf", b"%PDF-1.7"), db=db))

    created = _version(document_id=d.id)
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: d)
    monkeypatch.setattr(docs_api, "create_document_version", lambda **_k: created)
    monkeypatch.setattr(docs_api, "process_document", lambda **_k: None)
    out = _run(docs_api.create_new_document_version(d.id, file=_upload("new.pdf", b"%PDF-1.7"), db=db))
    assert out.id == created.id
    assert d.filename == "new.pdf"
    assert db.flushes >= 1

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.set_current_version(d.id, created.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda **_k: d)
    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.set_current_version(d.id, created.id, db=object())
    called = {"set_current": False}
    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: created)
    monkeypatch.setattr(docs_api, "set_current_document_version", lambda **_k: called.update(set_current=True))
    ok = docs_api.set_current_version(d.id, created.id, db=object())
    assert ok.status == "ok" and called["set_current"] is True

    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.download_document_version(d.id, created.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: created)
    assert isinstance(docs_api.download_document_version(d.id, created.id, db=object()), StreamingResponse)
    assert isinstance(docs_api.preview_document_version(d.id, created.id, db=object()), StreamingResponse)

    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: None)
    with pytest.raises(HTTPException):
        docs_api.get_document_version_tags(d.id, created.id, db=object())
    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: created)
    tags = docs_api.get_document_version_tags(d.id, created.id, db=object())
    assert tags.tags == ["invoice"]

    monkeypatch.setattr(docs_api, "replace_document_version_tags", lambda **_k: ["a"])
    monkeypatch.setattr(docs_api, "add_document_version_tags", lambda **_k: ["a", "b"])
    monkeypatch.setattr(docs_api, "remove_document_version_tags", lambda **_k: ["b"])
    assert docs_api.replace_tags_on_document_version(d.id, created.id, TagUpdateRequest(tags=["a"]), db=object()).tags == ["a"]
    assert docs_api.add_tags_to_document_version(d.id, created.id, TagUpdateRequest(tags=["b"]), db=object()).tags == ["a", "b"]
    assert docs_api.remove_tags_from_document_version(d.id, created.id, TagUpdateRequest(tags=["a"]), db=object()).tags == ["b"]

    wrong_doc = _version(document_id=uuid4())
    monkeypatch.setattr(docs_api, "get_document_version_by_id", lambda **_k: wrong_doc)
    with pytest.raises(HTTPException):
        docs_api.preview_document_version(d.id, created.id, db=object())
    with pytest.raises(HTTPException):
        docs_api.replace_tags_on_document_version(d.id, created.id, TagUpdateRequest(tags=["x"]), db=object())
    with pytest.raises(HTTPException):
        docs_api.add_tags_to_document_version(d.id, created.id, TagUpdateRequest(tags=["x"]), db=object())
    with pytest.raises(HTTPException):
        docs_api.remove_tags_from_document_version(d.id, created.id, TagUpdateRequest(tags=["x"]), db=object())


def test_validate_supported_upload_office_valid_returns(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(docs_api, "is_valid_office_file", lambda *_a, **_k: True)
    docs_api._validate_supported_upload(_upload("x.docx", b"zip"), b"zip")
