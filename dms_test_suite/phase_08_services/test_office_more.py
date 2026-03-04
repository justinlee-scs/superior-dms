from io import BytesIO
import zipfile

import pytest

from app.services.extraction.office import (
    OFFICE_EXTENSIONS,
    _extract_text_from_xml_parts,
    _load_xlsx_shared_strings,
    _local_name,
    _natural_sort_key,
    extract_text_from_office_file,
    is_valid_office_file,
)


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path, value in entries.items():
            zf.writestr(path, value)
    return buf.getvalue()


def test_extract_text_from_xlsx_and_pptx() -> None:
    xlsx = _zip_bytes(
        {
            "xl/workbook.xml": b"<workbook/>",
            "xl/worksheets/sheet1.xml": (
                b"<worksheet>"
                b"<sheetData><row>"
                b"<c t='s'><v>0</v></c>"
                b"<c><v>42</v></c>"
                b"</row></sheetData>"
                b"</worksheet>"
            ),
            "xl/sharedStrings.xml": (
                b"<sst><si><t>Hello</t></si><si><r><t>World</t></r></si></sst>"
            ),
        }
    )
    assert is_valid_office_file(xlsx, "a.xlsx") is True
    xlsx_text = extract_text_from_office_file(xlsx, "a.xlsx")
    assert "Hello" in xlsx_text
    assert "42" in xlsx_text

    pptx = _zip_bytes(
        {
            "ppt/presentation.xml": b"<p:presentation xmlns:p='x'/>",
            "ppt/slides/slide1.xml": b"<a:t xmlns:a='x'>Slide One</a:t>",
            "ppt/slides/slide2.xml": b"<a:t xmlns:a='x'>Slide Two</a:t>",
        }
    )
    assert is_valid_office_file(pptx, "a.pptx") is True
    pptx_text = extract_text_from_office_file(pptx, "a.pptx")
    assert "Slide One" in pptx_text
    assert "Slide Two" in pptx_text


def test_office_helpers_local_name_and_natural_sort() -> None:
    assert _local_name("{urn:test}tag") == "tag"
    assert _natural_sort_key("slide10.xml") > _natural_sort_key("slide2.xml")


def test_office_edge_paths_cover_validation_and_xml_read_branches(monkeypatch) -> None:
    # is_valid_office_file unknown extension branch (line 34).
    monkeypatch.setattr("app.services.extraction.office.OFFICE_EXTENSIONS", set(OFFICE_EXTENSIONS) | {".foo"})
    payload = _zip_bytes({"word/document.xml": b"<w:t xmlns:w='x'>x</w:t>"})
    assert is_valid_office_file(payload, "x.foo") is False

    # extract_text_from_office_file invalid file branch.
    with pytest.raises(ValueError):
        extract_text_from_office_file(b"not-a-zip", "bad.docx")

    # extract_text_from_office_file unsupported extension branch.
    monkeypatch.setattr("app.services.extraction.office.is_valid_office_file", lambda *_a, **_k: True)
    with pytest.raises(ValueError):
        extract_text_from_office_file(payload, "x.foo")

    # _load_xlsx_shared_strings KeyError + non-si branch.
    with zipfile.ZipFile(BytesIO(_zip_bytes({})), "r") as zf:
        assert _load_xlsx_shared_strings(zf) == []

    sst = _zip_bytes({"xl/sharedStrings.xml": b"<sst><x>skip</x><si><t>Keep</t></si></sst>"})
    with zipfile.ZipFile(BytesIO(sst), "r") as zf:
        assert _load_xlsx_shared_strings(zf) == ["Keep"]

    # _extract_text_from_xml_parts KeyError continue branch.
    xml_zip = _zip_bytes({"a.xml": b"<r><t>A</t></r>"})
    with zipfile.ZipFile(BytesIO(xml_zip), "r") as zf:
        assert _extract_text_from_xml_parts(zf, ["missing.xml", "a.xml"], {"t"}) == "A"
