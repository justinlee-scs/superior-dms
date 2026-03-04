from enum import Enum

from app.db.models.enums import DocumentClass
from app.services.extraction import tags as tags_mod


class _DocType(Enum):
    PAYROLL = "payroll"


def test_tag_helper_branches_cover_fallbacks_and_enums() -> None:
    assert tags_mod._as_string(None) is None
    assert tags_mod._as_string(_DocType.PAYROLL) == "payroll"
    assert tags_mod._as_string("x") == "x"

    assert tags_mod._derive_project_tag("project: acme", None).startswith("project:")
    assert tags_mod._derive_project_tag("", "project_zeus_invoice.pdf") == "project:zeus_invoice"
    assert tags_mod._derive_project_tag("", None) == "project:unassigned"

    assert tags_mod._derive_document_type_tag("manual", None) == "document_type:manual"
    assert tags_mod._derive_document_type_tag(None, "unknown") == "document_type:document"
    assert tags_mod._derive_document_type_tag(None, None) == "document_type:document"

    assert tags_mod._derive_security_clearance_tag("contains ssn", None, None) == "security_clearance:admin"
    assert tags_mod._derive_security_clearance_tag("", "manual", None) == "security_clearance:editor"
    assert tags_mod._derive_security_clearance_tag("", None, "contract") == "security_clearance:editor"
    assert tags_mod._derive_security_clearance_tag("", None, None) == "security_clearance:viewer"


def test_suggest_existing_tags_and_unassigned_removal() -> None:
    suggested = tags_mod._suggest_existing_tags(
        "customer account statement for west region",
        ["accounting", "project:alpha", "west_region", "  "],
    )
    assert "west_region" in suggested
    assert "project:alpha" not in suggested

    # Covers branch that discards project:unassigned if a specific project tag exists.
    derived = tags_mod.derive_tags(
        text="invoice text",
        classification=DocumentClass.INVOICE,
        filename="project_orion_invoice.pdf",
        existing_tags=["project:unassigned", "orion"],
    )
    assert "project:unassigned" not in derived


def test_suggest_existing_tags_extra_branches_and_project_unassigned_drop(monkeypatch) -> None:
    assert tags_mod._suggest_existing_tags("anything", None) == set()

    # Covers word-part matching branch where full phrase is not contiguous.
    suggested = tags_mod._suggest_existing_tags(
        "west and central region details",
        ["west_region"],
    )
    assert "west_region" in suggested

    # Force both project:unassigned and a specific project tag so discard branch executes.
    monkeypatch.setattr(tags_mod, "_derive_project_tag", lambda *_a, **_k: "project:unassigned")
    monkeypatch.setattr(tags_mod, "_suggest_existing_tags", lambda *_a, **_k: {"project:alpha"})
    derived = tags_mod.derive_tags("doc", DocumentClass.UNKNOWN, filename="x.pdf")
    assert "project:alpha" in derived
    assert "project:unassigned" not in derived
