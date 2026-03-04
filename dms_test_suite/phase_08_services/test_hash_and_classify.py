from app.db.models.enums import DocumentClass
from app.services.extraction.classify import classify_document
from app.services.hash import compute_content_hash


def test_compute_content_hash_is_stable_and_sha256_length() -> None:
    payload = b"hello world"
    h1 = compute_content_hash(payload)
    h2 = compute_content_hash(payload)

    assert h1 == h2
    assert len(h1) == 64
    assert h1 != compute_content_hash(b"hello world!")


def test_classify_document_heuristics() -> None:
    assert classify_document("Invoice #123 due date") == DocumentClass.INVOICE
    assert classify_document("Store receipt subtotal tax total") == DocumentClass.RECEIPT
    assert classify_document("This agreement is a contract") == DocumentClass.CONTRACT
    assert classify_document("totally unrelated text") == DocumentClass.UNKNOWN
