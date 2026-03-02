// File: dms.ts
import { apiFetch } from "./api";

export function listDocuments() {
  return apiFetch("/documents/");
}

export function getDocument(id: string) {
  return apiFetch(`/documents/${id}`);
}

export function getDocumentOutput(id: string) {
  return apiFetch(`/documents/${id}/output`);
}

export type DocumentVersion = {
  id: string;
  document_id: string;
  version_number: number;
  is_current: boolean;
  processing_status: string;
  classification: string | null;
  confidence: number | null;
  created_at: string;
  size_bytes: number;
};

export function listDocumentVersions(documentId: string) {
  return apiFetch<DocumentVersion[]>(`/documents/${documentId}/versions`);
}

export function setCurrentDocumentVersion(documentId: string, versionId: string) {
  return apiFetch(`/documents/${documentId}/versions/${versionId}/set-current`, {
    method: "POST",
  });
}

export async function uploadDocumentVersion(documentId: string, file: File) {
  const form = new FormData();
  form.append("file", file);

  const token = sessionStorage.getItem("access_token");
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/documents/${documentId}/versions`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });

  if (res.status === 401) {
    sessionStorage.removeItem("access_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Version upload failed");
  }

  return res.json();
}

export async function downloadDocumentVersion(documentId: string, versionId: string) {
  const token = sessionStorage.getItem("access_token");
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/documents/${documentId}/versions/${versionId}/download`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  if (res.status === 401) {
    sessionStorage.removeItem("access_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Version download failed");
  }

  return res.blob();
}

export function deleteDocument(id: string) {
  return apiFetch(`/documents/${id}`, { method: "DELETE" });
}

export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${sessionStorage.getItem("access_token")}`,
    },
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
