import { API_BASE_URL } from "./api";

/**
 * Upload a document file
 */
export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Upload failed");
  }

  return res.json();
}

/**
 * Get a single document by ID
 */
export async function getDocument(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Fetch failed");
  }
  return res.json();
}

/**
 * Get processed output of a document version
 */
export async function getDocumentOutput(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}/output`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Output fetch failed");
  }
  return res.json();
}

/**
 * Delete a document
 */
export async function deleteDocument(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Delete failed");
  }
}

/**
 * List all documents
 */
export async function listDocuments() {
  const res = await fetch(`${API_BASE_URL}/documents/`); // trailing slash matches FastAPI
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "List failed");
  }
  return res.json();
}
