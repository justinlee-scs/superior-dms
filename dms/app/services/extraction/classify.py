from app.db.models.enums import DocumentClass


def classify_document(text: str) -> DocumentClass:
    """
    Very simple heuristic classifier.
    Replace with ML later.
    """

    lowered = text.lower()

    if "invoice" in lowered:
        return DocumentClass.INVOICE

    if "receipt" in lowered:
        return DocumentClass.RECEIPT

    if "agreement" in lowered or "contract" in lowered:
        return DocumentClass.CONTRACT

    return DocumentClass.UNKNOWN
