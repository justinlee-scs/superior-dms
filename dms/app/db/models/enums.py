import enum
from enum import Enum

class DocumentClass(str, Enum):
    """Top-level labels produced by document content classification.

    Parameters:
        INVOICE: Enumeration member representing an allowed constant value.
        CONTRACT: Enumeration member representing an allowed constant value.
        RECEIPT: Enumeration member representing an allowed constant value.
        UNKNOWN: Enumeration member representing an allowed constant value.
    """
    INCOMING_INVOICE = "incoming_invoice"
    OUTGOING_INVOICE = "outgoing_invoice"
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"

class ProcessingStage(str, enum.Enum):
    """Named pipeline stages tracked during document processing.

    Parameters:
        CLASSIFICATION: Predicted document class label.
        OCR: Enumeration member representing an allowed constant value.
        TAGGING: Enumeration member representing an allowed constant value.
        POST_PROCESS: Enumeration member representing an allowed constant value.
    """
    CLASSIFICATION = "CLASSIFICATION"
    OCR = "OCR"
    TAGGING = "TAGGING"
    POST_PROCESS = "POST_PROCESS"


class ProcessingStatus(str, enum.Enum):
    """Execution states used to report processing progress/outcomes.

    Parameters:
        pending: Enumeration member used by the processing/authorization flow.
        processing: Enumeration member used by the processing/authorization flow.
        uploaded: Enumeration member used by the processing/authorization flow.
        failed: Enumeration member used by the processing/authorization flow.
    """
    pending = "pending"
    processing = "processing"
    uploaded = "uploaded"
    failed = "failed"
