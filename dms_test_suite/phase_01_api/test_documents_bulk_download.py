from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api import documents as docs_api
from app.schemas.documents import BulkDownloadRequest


class _DB:
    def __init__(self):
        self.get_map = {}


def test_unique_zip_entry_name_handles_collisions() -> None:
    used = set()
    first = docs_api._unique_zip_entry_name("report.pdf", "fallback.bin", used)
    second = docs_api._unique_zip_entry_name("report.pdf", "fallback.bin", used)
    third = docs_api._unique_zip_entry_name("report.pdf", "fallback.bin", used)

    assert first == "report.pdf"
    assert second == "report (2).pdf"
    assert third == "report (3).pdf"


def test_bulk_download_documents_success(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _DB()
    doc_id = uuid4()
    other_id = uuid4()
    document = SimpleNamespace(id=doc_id, filename="report.pdf")
    other_document = SimpleNamespace(id=other_id, filename="report.pdf")
    version = SimpleNamespace(content=b"abc")
    other_version = SimpleNamespace(content=b"xyz")

    monkeypatch.setattr(docs_api, "get_document_by_id", lambda db, document_id: document if document_id == doc_id else other_document)
    monkeypatch.setattr(docs_api, "get_document_version", lambda db, document_id: version if document_id == doc_id else other_version)

    payload = BulkDownloadRequest(document_ids=[doc_id, doc_id, other_id])
    response = docs_api.bulk_download_documents(payload, db=db)
    iterator = response.body_iterator
    if hasattr(iterator, "__aiter__"):
        import anyio

        async def _collect():
            data = b""
            async for chunk in iterator:
                data += chunk
            return data

        body = anyio.run(_collect)
    else:
        body = b"".join(iterator)

    assert b"report.pdf" in body
    assert b"report (2).pdf" in body
    assert b"abc" in body
    assert b"xyz" in body


def test_bulk_download_documents_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _DB()
    doc_id = uuid4()
    monkeypatch.setattr(docs_api, "get_document_by_id", lambda db, document_id: None)

    with pytest.raises(docs_api.HTTPException):
        docs_api.bulk_download_documents(BulkDownloadRequest(document_ids=[doc_id]), db=db)
