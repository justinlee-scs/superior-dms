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
  due_date?: string | null;
};

export type DuePaymentItem = {
  document_id: string;
  version_id: string;
  filename: string;
  due_date: string;
};

export type WorkspaceUpdateResponse = {
  id: string;
  in_workspace: boolean;
};

export type ProjectMoveResponse = {
  document_id: string;
  version_id: string;
  project_tag: string;
  tags: string[];
};

export type WorkflowUpdateResponse = {
  document_id: string;
  version_id: string;
  status: "failed" | "pending" | "uploaded" | "needs review";
  notes: string | null;
};

export type RetrainSchedule = {
  enabled: boolean;
  timezone: string;
  hour: number;
  minute: number;
  updated_at?: string | null;
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

  const res = await fetch(
    `${import.meta.env.VITE_API_BASE_URL}/documents/${documentId}/versions`,
    {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form,
    }
  );

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

export function listTagPool(query?: string) {
  const q = query?.trim();
  const suffix = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiFetch<{ tags: string[] }>(`/documents/tag-pool${suffix}`);
}

export function createTagPool(tag: string) {
  return apiFetch<{ tag: string }>("/documents/tag-pool", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag }),
  });
}

export function replaceDocumentVersionTags(
  documentId: string,
  versionId: string,
  tags: string[],
) {
  return apiFetch<{ document_id: string; version_id: string; tags: string[] }>(
    `/documents/${documentId}/versions/${versionId}/tags`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags }),
    },
  );
}

export function updateDocumentVersionDueDate(
  documentId: string,
  versionId: string,
  dueDate: string | null,
) {
  return apiFetch<{ due_date: string | null; tags: string[] }>(
    `/documents/${documentId}/versions/${versionId}/due-date`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ due_date: dueDate }),
    },
  );
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

export async function bulkDownloadDocuments(documentIds: string[]) {
  const token = sessionStorage.getItem("access_token");
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/documents/bulk-download`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ document_ids: documentIds }),
  });

  if (res.status === 401) {
    sessionStorage.removeItem("access_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Bulk download failed");
  }

  return res.blob();
}

export function listUpcomingDuePayments(daysAhead = 30, limit = 50) {
  const params = new URLSearchParams({
    days_ahead: String(daysAhead),
    limit: String(limit),
  });
  return apiFetch<DuePaymentItem[]>(`/documents/upcoming-due-payments?${params.toString()}`);
}

export function getRetrainSchedule() {
  return apiFetch<RetrainSchedule>("/admin/training/schedule");
}

export function updateRetrainSchedule(payload: {
  enabled: boolean;
  timezone: string;
  hour: number;
  minute: number;
}) {
  return apiFetch<RetrainSchedule>("/admin/training/schedule", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function reprocessDocument(documentId: string) {
  return apiFetch<{ document_id: string; status: string }>(`/processing/documents/${documentId}/reprocess`, {
    method: "POST",
  });
}

export function updateDocumentWorkspace(
  documentId: string,
  inWorkspace: boolean,
) {
  return apiFetch<WorkspaceUpdateResponse>(`/documents/${documentId}/workspace`, {
    method: "PUT",
    body: JSON.stringify({ in_workspace: inWorkspace }),
  });
}

export function moveDocumentProject(documentId: string, projectName: string) {
  return apiFetch<ProjectMoveResponse>(`/documents/${documentId}/project`, {
    method: "PATCH",
    body: JSON.stringify({ project_name: projectName }),
  });
}

export function updateDocumentWorkflow(
  documentId: string,
  payload: { status: "failed" | "pending" | "uploaded" | "needs review"; notes: string },
) {
  return apiFetch<WorkflowUpdateResponse>(`/documents/${documentId}/workflow`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
