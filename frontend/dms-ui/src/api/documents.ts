export interface DocumentResponse {
  id: string;
  filename: string;
  status: string;
  document_type: string | null;
  confidence: number | null;
  created_at: string;
}

const API_BASE = "http://localhost:8008/api";

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Upload failed");
  }

  return res.json();
}

export async function listDocuments(): Promise<DocumentResponse[]> {
  const res = await fetch(`${API_BASE}/documents`);

  if (!res.ok) {
    throw new Error("Failed to load documents");
  }

  return res.json();
}
