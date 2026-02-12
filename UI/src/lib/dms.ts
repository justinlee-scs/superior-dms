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
