from io import BytesIO
import zipfile

from app.db.models.enums import DocumentClass
from app.services.extraction.office import extract_text_from_office_file, is_valid_office_file
from app.services.extraction.tags import derive_tags, normalize_tag


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, value in entries.items():
            zf.writestr(path, value)
    return buf.getvalue()


def test_is_valid_office_file_for_docx_and_invalid_zip() -> None:
    valid_docx = _zip_bytes({"word/document.xml": b"<w:doc xmlns:w='x'><w:t>Hello</w:t></w:doc>"})
    invalid_docx = b"not-a-zip"

    assert is_valid_office_file(valid_docx, "x.docx") is True
    assert is_valid_office_file(invalid_docx, "x.docx") is False
    assert is_valid_office_file(valid_docx, "x.pdf") is False


def test_extract_text_from_office_file_docx() -> None:
    payload = _zip_bytes(
        {
            "word/document.xml": b"<w:doc xmlns:w='x'><w:t>Hello</w:t><w:t>World</w:t></w:doc>",
            "word/header1.xml": b"<w:hdr xmlns:w='x'><w:t>Header</w:t></w:hdr>",
        }
    )

    text = extract_text_from_office_file(payload, "file.docx")

    assert "Hello" in text
    assert "World" in text
    assert "Header" in text


def test_normalize_and_derive_tags_include_mandatory_families() -> None:
    assert normalize_tag("  Project: Alpha Team!  ") == "project:_alpha_team"

    tags = derive_tags(
        text="Invoice for Project ACME with due date and amount due",
        classification=DocumentClass.INVOICE,
        document_type=None,
        filename="project_acme_invoice.pdf",
        existing_tags=["urgent", "project:ignored"],
    )

    assert any(t.startswith("project:") for t in tags)
    assert any(t.startswith("document_type:") for t in tags)
    assert any(t.startswith("security_clearance:") for t in tags)
    assert "invoice" in tags
