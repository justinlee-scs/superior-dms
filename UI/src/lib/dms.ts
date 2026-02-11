import { apiFetch } from "./api";

/**
 * Upload a document file
 */
export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);

  const token = sessionStorage.getItem("access_token");

  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: token
      ? { Authorization: `Bearer ${token}` }
      : undefined,
    body: form,
  });

  if (res.status === 401) {
    sessionStorage.removeItem("access_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Upload failed");
  }

  return res.json();
}

/**
 * Get a single document by ID
 */
export function getDocument(id: string) {
  return apiFetch(`/documents/${id}`);
}

/**
 * Get processed output
 */
export function getDocumentOutput(id: string) {
  return apiFetch(`/documents/${id}/output`);
}

/**
 * Delete a document
 */
export function deleteDocument(id: string) {
  return apiFetch(`/documents/${id}`, {
    method: "DELETE",
  });
}

/**
 * List all documents
 */
export function listDocuments() {
  return apiFetch(`/documents/`);
}
