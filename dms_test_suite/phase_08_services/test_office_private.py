import zipfile
from io import BytesIO

from app.services.extraction import office


def _zip_bytes(files: dict[str, str]) -> bytes:
    buff = BytesIO()
    with zipfile.ZipFile(buff, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buff.getvalue()


def test_extract_docx_private() -> None:
    data = _zip_bytes(
        {
            "word/document.xml": "<w:document xmlns:w='w'><w:t>Hello</w:t></w:document>",
            "word/header1.xml": "<w:hdr xmlns:w='w'><w:t>Header</w:t></w:hdr>",
        }
    )
    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        text = office._extract_docx(zf, zf.namelist())
    assert "Hello" in text
    assert "Header" in text


def test_extract_xlsx_private() -> None:
    data = _zip_bytes(
        {
            "xl/sharedStrings.xml": "<sst><si><t>Alpha</t></si></sst>",
            "xl/worksheets/sheet1.xml": "<worksheet><c t='s'><v>0</v></c></worksheet>",
        }
    )
    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        text = office._extract_xlsx(zf, zf.namelist())
    assert "Alpha" in text


def test_extract_pptx_private() -> None:
    data = _zip_bytes(
        {
            "ppt/slides/slide1.xml": "<p:sld xmlns:p='p'><p:t>Slide</p:t></p:sld>",
            "ppt/slides/slide2.xml": "<p:sld xmlns:p='p'><p:t>Two</p:t></p:sld>",
        }
    )
    with zipfile.ZipFile(BytesIO(data), "r") as zf:
        text = office._extract_pptx(zf, zf.namelist())
    assert "Slide" in text
    assert "Two" in text
