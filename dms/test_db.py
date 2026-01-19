from app.ingest import ingest_file
from app.process import ocr_document

doc_id = ingest_file(
    path="snoopy.pdf",
    mime_type="application/pdf",
    doc_class="test"
)

ocr_document(doc_id, "snoopy.pdf")

print("Ingested and OCR processed:", doc_id)