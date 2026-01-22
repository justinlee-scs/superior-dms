import enum
from enum import Enum

class DocumentClass(str, Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"

class ProcessingStage(str, enum.Enum):
    CLASSIFICATION = "CLASSIFICATION"
    OCR = "OCR"
    POST_PROCESS = "POST_PROCESS"


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    uploaded = "uploaded"
    failed = "failed"