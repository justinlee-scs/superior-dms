import { API_BASE_URL } from "./api";

export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error("Upload failed");
  }

  return res.json();
}

export async function getDocument(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`);
  if (!res.ok) throw new Error("Fetch failed");
  return res.json();
}

export async function getDocumentOutput(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}/output`);
  if (!res.ok) throw new Error("Output fetch failed");
  return res.json();
}

export async function deleteDocument(id: string) {
  const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Delete failed");
}

export async function listDocuments() {
  const res = await fetch(`${API_BASE_URL}/documents`);
  if (!res.ok) throw new Error("List failed");
  return res.json();
}

