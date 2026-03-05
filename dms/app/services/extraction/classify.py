from app.db.models.enums import DocumentClass


def classify_document(text: str) -> DocumentClass:
    """Very simple heuristic classifier.

    Parameters:
        text (type=str): Function argument used by this operation.
    """

    lowered = text.lower()

    if "invoice" in lowered:
        return DocumentClass.INVOICE

    if "receipt" in lowered:
        return DocumentClass.RECEIPT

    if "agreement" in lowered or "contract" in lowered:
        return DocumentClass.CONTRACT

    return DocumentClass.UNKNOWN
