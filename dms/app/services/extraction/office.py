from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET


OFFICE_EXTENSIONS = {".docx", ".xlsx", ".pptx"}


def is_valid_office_file(file_bytes: bytes, filename: str) -> bool:
    """Return whether valid office file.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
    """
    suffix = Path(filename or "").suffix.lower()
    if suffix not in OFFICE_EXTENSIONS:
        return False

    try:
        with zipfile.ZipFile(BytesIO(file_bytes), "r") as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return False

    if suffix == ".docx":
        return "word/document.xml" in names
    if suffix == ".xlsx":
        return "xl/workbook.xml" in names and any(
            name.startswith("xl/worksheets/") for name in names
        )
    if suffix == ".pptx":
        return "ppt/presentation.xml" in names and any(
            name.startswith("ppt/slides/slide") for name in names
        )
    return False


def extract_text_from_office_file(file_bytes: bytes, filename: str) -> str:
    """Extract text from office file.

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
        filename (type=str): File or entity name used for storage and display.
    """
    suffix = Path(filename or "").suffix.lower()

    if not is_valid_office_file(file_bytes, filename):
        raise ValueError(f"Unsupported or invalid Office file: {suffix or 'unknown'}")

    with zipfile.ZipFile(BytesIO(file_bytes), "r") as zf:
        names = zf.namelist()
        if suffix == ".docx":
            return _extract_docx(zf, names)
        if suffix == ".xlsx":
            return _extract_xlsx(zf, names)
        if suffix == ".pptx":
            return _extract_pptx(zf, names)

    raise ValueError(f"Unsupported Office extension: {suffix}")


def _extract_docx(zf: zipfile.ZipFile, names: list[str]) -> str:
    """Handle extract docx.

    Parameters:
        zf (type=zipfile.ZipFile): Function argument used by this operation.
        names (type=list[str]): Function argument used by this operation.
    """
    xml_paths = ["word/document.xml"] + sorted(
        name
        for name in names
        if name.startswith("word/header") or name.startswith("word/footer")
    )
    return _extract_text_from_xml_parts(zf, xml_paths, allowed_local_tags={"t"})


def _extract_xlsx(zf: zipfile.ZipFile, names: list[str]) -> str:
    """Handle extract xlsx.

    Parameters:
        zf (type=zipfile.ZipFile): Function argument used by this operation.
        names (type=list[str]): Function argument used by this operation.
    """
    parts: list[str] = []
    shared_strings = _load_xlsx_shared_strings(zf)

    sheet_paths = sorted(
        (name for name in names if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")),
        key=_natural_sort_key,
    )
    for path in sheet_paths:
        xml_bytes = zf.read(path)
        root = ET.fromstring(xml_bytes)
        for cell in root.iter():
            if _local_name(cell.tag) != "c":
                continue
            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                value_node = next((c for c in cell if _local_name(c.tag) == "v"), None)
                if value_node is not None and value_node.text and value_node.text.isdigit():
                    idx = int(value_node.text)
                    if 0 <= idx < len(shared_strings):
                        parts.append(shared_strings[idx])
            else:
                for child in cell:
                    if _local_name(child.tag) in {"v", "t"} and child.text:
                        parts.append(child.text.strip())

    return "\n".join(filter(None, parts))


def _load_xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Handle load xlsx shared strings.

    Parameters:
        zf (type=zipfile.ZipFile): Function argument used by this operation.
    """
    try:
        xml_bytes = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(xml_bytes)
    strings: list[str] = []
    for si in root:
        if _local_name(si.tag) != "si":
            continue
        text_parts = []
        for node in si.iter():
            if _local_name(node.tag) == "t" and node.text:
                text_parts.append(node.text)
        strings.append("".join(text_parts).strip())
    return strings


def _extract_pptx(zf: zipfile.ZipFile, names: list[str]) -> str:
    """Handle extract pptx.

    Parameters:
        zf (type=zipfile.ZipFile): Function argument used by this operation.
        names (type=list[str]): Function argument used by this operation.
    """
    slide_paths = sorted(
        (
            name
            for name in names
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ),
        key=_natural_sort_key,
    )
    return _extract_text_from_xml_parts(zf, slide_paths, allowed_local_tags={"t"})


def _extract_text_from_xml_parts(
    zf: zipfile.ZipFile,
    paths: list[str],
    allowed_local_tags: set[str],
) -> str:
    """Handle extract text from xml parts.

    Parameters:
        zf (type=zipfile.ZipFile): Function argument used by this operation.
        paths (type=list[str]): Function argument used by this operation.
        allowed_local_tags (type=set[str]): Function argument used by this operation.
    """
    parts: list[str] = []
    for path in paths:
        try:
            xml_bytes = zf.read(path)
        except KeyError:
            continue

        root = ET.fromstring(xml_bytes)
        for node in root.iter():
            if _local_name(node.tag) in allowed_local_tags and node.text:
                value = node.text.strip()
                if value:
                    parts.append(value)

    return "\n".join(parts)


def _local_name(tag: str) -> str:
    """Handle local name.

    Parameters:
        tag (type=str): Function argument used by this operation.
    """
    return tag.rsplit("}", 1)[-1]


def _natural_sort_key(value: str) -> list[str | int]:
    """Handle natural sort key.

    Parameters:
        value (type=str): Function argument used by this operation.
    """
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]
