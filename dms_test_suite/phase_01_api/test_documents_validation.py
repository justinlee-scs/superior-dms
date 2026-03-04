import io

import pytest
from fastapi import HTTPException, UploadFile

from app.api.documents import _validate_supported_upload


def _upload(filename: str, data: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data))


def test_validate_supported_upload_rejects_unsupported_extension() -> None:
    file = _upload("invoice.txt", b"hello")

    with pytest.raises(HTTPException) as exc:
        _validate_supported_upload(file, b"hello")

    assert exc.value.status_code == 415
    assert "Unsupported file type" in exc.value.detail


def test_validate_supported_upload_rejects_invalid_pdf_header() -> None:
    file = _upload("invoice.pdf", b"not-a-real-pdf")

    with pytest.raises(HTTPException) as exc:
        _validate_supported_upload(file, b"not-a-real-pdf")

    assert exc.value.status_code == 415
    assert "not a valid PDF header" in exc.value.detail


def test_validate_supported_upload_accepts_valid_pdf_header() -> None:
    file = _upload("invoice.pdf", b"%PDF-1.7\n...")

    _validate_supported_upload(file, b"%PDF-1.7\n...")


def test_validate_supported_upload_rejects_invalid_image_payload() -> None:
    file = _upload("image.png", b"not-an-image")

    with pytest.raises(HTTPException) as exc:
        _validate_supported_upload(file, b"not-an-image")

    assert exc.value.status_code == 415
    assert "invalid image file" in exc.value.detail


def test_validate_supported_upload_uses_office_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.documents.is_valid_office_file", lambda *_args, **_kwargs: False)
    file = _upload("doc.docx", b"office-bytes")

    with pytest.raises(HTTPException) as exc:
        _validate_supported_upload(file, b"office-bytes")

    assert exc.value.status_code == 415
    assert "invalid Office file" in exc.value.detail
