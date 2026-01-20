const API_BASE = "http://localhost:8008/api";

export type DocumentType =
  | "document"
  | "statement"
  | "outgoing_invoice"
  | "incoming_invoice"
  | "contract"
  | "payroll"
  | "manual"
  | "receipt"
  | "other";

export interface DocumentResponse {
  id: string;
  filename: string;
  status: string | null;
  document_type: DocumentType | null;
  confidence: number | null;
  created_at: string;
  current_version_id: string | null;
}

export async function fetchDocuments(): Promise<DocumentResponse[]> {
  const res = await fetch(`${API_BASE}/documents/`);
  if (!res.ok) {
    throw new Error("Failed to fetch documents");
  }
  return res.json();
}

export async function uploadDocument(
  file: File,
  documentType: DocumentType
): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }

  return res.json();
}

