import { useState, useMemo, useEffect, useRef } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";

import { DocumentCard, type Document } from "@/app/components/document-card";
import { GroupedDocuments } from "@/app/components/grouped-documents";
import { CompactProjectView } from "@/app/components/compact-project-view";
import {
  SearchFilters,
  type FilterState,
} from "@/app/components/search-filters";
import { UploadZone } from "@/app/components/upload-zone";
import { WorkflowEditor } from "@/app/components/workflow-editor";
import { BulkActionBar } from "@/app/components/bulk-action-bar";
import { VersionHistoryModal } from "@/app/components/version-history-modal";
import { ProfileDialog } from "@/app/components/profile-dialog";
import { TagEditorDialog } from "@/app/components/tag-editor-dialog";
import {
  UpcomingDuePaymentsPanel,
  type DuePayment,
} from "@/app/components/upcoming-due-payments-panel";

import {
  SelectionProvider,
  useSelection,
} from "@/app/selection/selection-context";

import { Button } from "@/app/components/ui/button";
import {
  Drawer,
  DrawerContent,
} from "@/app/components/ui/drawer";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/app/components/ui/tabs";
import { Toaster } from "@/app/components/ui/sonner";

import {
  FileText,
  Upload as UploadIcon,
  Layers,
  Bookmark,
  AlignJustify,
  Moon,
  Sun,
  CheckCircle2,
  AlertTriangle,
  Shield,
  UserCircle2,
  SlidersHorizontal,
} from "lucide-react";

import { toast } from "sonner";
import {
  addDocumentVersionTags,
  bulkDownloadDocuments,
  createTagPool,
  deleteTagPool,
  deleteDocument,
  listDocuments,
  listUpcomingDuePayments,
  reprocessDocument,
  listTagPool,
  moveDocumentProject,
  removeDocumentVersionTags,
  replaceDocumentVersionTags,
  updateDocumentVersionDueDate,
  updateDocumentWorkflow,
  updateDocumentWorkspace,
  uploadDocument,
} from "@/lib/dms";
import { API_BASE_URL } from "@/lib/api";
import { getMyAccess } from "@/lib/rbac";
import { formatBytes } from "@/lib/format";
import { normalizeWorkflowStatus } from "@/lib/dms";
import { openLoadingPreviewWindow } from "@/lib/preview";
import { getCurrentUserProfile, updateCurrentUserProfile } from "@/lib/profile";
import { isOfficeFilename } from "@/lib/file-types";
import { saveResponseAsFile } from "@/lib/file-transfer";
import {
  applyUiThemeClass,
  persistUiPreferences,
  readUiPreferences,
} from "@/lib/ui-preferences";
import RolesPage from "@/admin/roles-page";

/**
 * Maps backend document → UI Document
 */
function getProjectFromTags(tags: string[] | undefined): string {
  const projectTag = (tags ?? []).find((tag) =>
    tag.toLowerCase().startsWith("project:"),
  );
  if (!projectTag) return "unassigned";

  const raw = projectTag.slice("project:".length).trim();
  if (!raw || raw === "unassigned") return "unassigned";

  return raw
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toLocalDateOnly(value?: string | null): string {
  if (!value) return "";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";
  const year = dt.getFullYear();
  const month = String(dt.getMonth() + 1).padStart(2, "0");
  const day = String(dt.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function mapApiDocument(doc: any): Document {
  const extension = (doc.filename?.split(".").pop() ?? "file").toLowerCase();
  const tags = doc.tags ?? [];
  return {
    id: doc.id,
    name: doc.filename,
    type: extension,
    size: formatBytes(doc.size_bytes ?? null),
    sizeBytes: doc.size_bytes ?? null,
    author: doc.author ?? "System",
    date: toLocalDateOnly(doc.created_at),
    tags,
    workflow: normalizeWorkflowStatus(doc.status),
    project: getProjectFromTags(tags),
    documentType: doc.document_type ?? "Document",
    vendor: doc.vendor,
    projectNumber: doc.project_number,
    currentVersionId: doc.current_version_id,
    currentVersionNumber: doc.current_version_number ?? 1,
    versionCount: doc.version_count ?? 1,
    dueDate: doc.due_date ?? null,
    pageCount: doc.page_count ?? null,
    inWorkspace: Boolean(doc.in_workspace),
    workflowNotes: doc.workflow_notes ?? null,
  };
}

function AppInner() {
  const initialUiPreferences = readUiPreferences();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [deletedQueue, setDeletedQueue] = useState<
    { doc: Document; timeoutId: ReturnType<typeof setTimeout> }[]
  >([]);
  const [filters, setFilters] = useState<FilterState>({
    searchText: "",
    selectedTags: [],
    author: "",
    dateRange: "",
    startDate: undefined,
    endDate: undefined,
    tagMatchMode: "any",
  });

  const [selectedDocument, setSelectedDocument] = useState<Document | null>(
    null,
  );
  const [workflowEditorOpen, setWorkflowEditorOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"compact" | "grouped">(
    () => initialUiPreferences.viewMode,
  );
  const [darkMode, setDarkMode] = useState<boolean>(
    () => initialUiPreferences.darkMode,
  );
  const [isAdmin, setIsAdmin] = useState(false);
  const [versionModalDoc, setVersionModalDoc] = useState<Document | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"documents" | "workspace" | "upload" | "admin">(
    "documents",
  );
  const [tagPool, setTagPool] = useState<string[]>([]);
  const [editingTagsDoc, setEditingTagsDoc] = useState<Document | null>(null);
  const [duePayments, setDuePayments] = useState<DuePayment[]>([]);
  const [duePaymentsLoading, setDuePaymentsLoading] = useState(false);
  const [accessPermissions, setAccessPermissions] = useState<Set<string>>(
    new Set(),
  );
  const [duePaymentsWindowDays, setDuePaymentsWindowDays] = useState(7);
  const [liveSyncEnabled, setLiveSyncEnabled] = useState(true);
  const preferencesReadyRef = useRef(false);
  const skipNextPreferencePersistRef = useRef(false);
  const searchTextRef = useRef("");

  const msUntilNextMidnight = () => {
    const now = new Date();
    const next = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + 1,
      0,
      0,
      1,
      0,
    );
    return next.getTime() - now.getTime();
  };

  const handleLogout = () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
    window.location.reload();
  };

  const selection = useSelection();

  /**
   * Load documents
   */
  const refreshDocuments = async (query = searchTextRef.current) => {
    const apiDocs = (await listDocuments(query.trim() || undefined)) as any[];
    const baseDocs = apiDocs.map(mapApiDocument);
    setDocuments(baseDocs);
  };

  // wait until backend actually returns the uploaded file
  const waitForDocument = async (
    filename: string,
    retries = 6,
    delay = 300,
  ): Promise<any[] | null> => {
    for (let i = 0; i < retries; i++) {
      const docs = (await listDocuments()) as any[];

      if (docs.some((d) => d.filename === filename)) {
        return docs;
      }

      await new Promise((res) => setTimeout(res, delay));
    }

    return null;
  };

  const refreshTagPool = async () => {
    const data = await listTagPool();
    setTagPool(data.tags ?? []);
  };

  const refreshDuePayments = async () => {
    if (!accessPermissions.has("document.due_payments")) {
      setDuePayments([]);
      setDuePaymentsLoading(false);
      return;
    }
    setDuePaymentsLoading(true);
    try {
      const items = await listUpcomingDuePayments(duePaymentsWindowDays, 12);
      setDuePayments(
        items.map((item) => ({
          documentId: item.document_id,
          versionId: item.version_id,
          filename: item.filename,
          dueDate: item.due_date,
        })),
      );
    } finally {
      setDuePaymentsLoading(false);
    }
  };

  const pollDocumentStatus = async (documentId: string) => {
    const maxAttempts = 45;
    const delayMs = 2000;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const docs = (await listDocuments()) as any[];
      const current = docs.find((doc) => doc.id === documentId);
      if (!current) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        continue;
      }

      const next = mapApiDocument(current);
      setDocuments((prev) =>
        prev.map((doc) => (doc.id === documentId ? next : doc)),
      );

      if (normalizeWorkflowStatus(next.workflow).toLowerCase() !== "processing") {
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    toast.info("Processing is still running in the background.");
  };

  useEffect(() => {
    refreshDocuments().catch(() => toast.error("Failed to load documents"));
    refreshTagPool().catch(() => toast.error("Failed to load tags"));
    refreshDuePayments().catch(() =>
      toast.error("Failed to load due payments"),
    );
  }, []);

  useEffect(() => {
    getMyAccess()
      .then((access) => {
        const hasAdminUsers = access.permissions.includes("admin.users");
        const hasAdminRoles = access.permissions.includes("admin.roles");
        const hasAdminTraining = access.permissions.includes("admin.training");
        setAccessPermissions(new Set(access.permissions));
        setIsAdmin(hasAdminUsers || hasAdminRoles || hasAdminTraining);
      })
      .catch(() => {
        setIsAdmin(false);
        setAccessPermissions(new Set());
      });
  }, []);

  useEffect(() => {
    refreshDocuments().catch(() => toast.error("Failed to load documents"));
    refreshTagPool().catch(() => toast.error("Failed to load tags"));
    refreshDuePayments().catch(() =>
      toast.error("Failed to load due payments"),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessPermissions, duePaymentsWindowDays]);

  useEffect(() => {
    if (!liveSyncEnabled) return;

    const intervalId = window.setInterval(() => {
      refreshDocuments().catch(() => undefined);
      refreshTagPool().catch(() => undefined);
    }, 3000);

    const onVisible = () => {
      if (document.visibilityState === "visible") {
        refreshDocuments().catch(() => undefined);
        refreshTagPool().catch(() => undefined);
      }
    };

    window.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onVisible);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onVisible);
    };
  }, [liveSyncEnabled]);

  useEffect(() => {
    getCurrentUserProfile()
      .then((user) => {
        const nextDarkMode = Boolean(user.ui_dark_mode);
        const nextViewMode = user.ui_view_mode === "grouped" ? "grouped" : "compact";
        skipNextPreferencePersistRef.current = true;
        setDarkMode(nextDarkMode);
        setViewMode(nextViewMode);
        persistUiPreferences({
          darkMode: nextDarkMode,
          viewMode: nextViewMode,
        });
        applyUiThemeClass(nextDarkMode);
      })
      .finally(() => {
        preferencesReadyRef.current = true;
      });
  }, []);

  useEffect(() => {
    persistUiPreferences({ darkMode, viewMode });
    applyUiThemeClass(darkMode);

    if (!preferencesReadyRef.current) return;
    if (skipNextPreferencePersistRef.current) {
      skipNextPreferencePersistRef.current = false;
      return;
    }
    updateCurrentUserProfile({
      ui_dark_mode: darkMode,
      ui_view_mode: viewMode,
    }).catch(() => undefined);
  }, [darkMode, viewMode]);

  useEffect(() => {
    searchTextRef.current = filters.searchText;
  }, [filters.searchText]);

  useEffect(() => {
    let timeoutId: number | null = null;
    let intervalId: number | null = null;
    let cancelled = false;

    const scheduleDailyRefresh = () => {
      timeoutId = window.setTimeout(() => {
        if (cancelled) return;
        refreshDuePayments().catch(() => undefined);
        intervalId = window.setInterval(() => {
          refreshDuePayments().catch(() => undefined);
        }, 24 * 60 * 60 * 1000);
      }, msUntilNextMidnight());
    };

    scheduleDailyRefresh();
    return () => {
      cancelled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      if (intervalId !== null) window.clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessPermissions, duePaymentsWindowDays]);

  /**
   * Filters
   */
  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    documents.forEach((d) => d.tags.forEach((t) => tags.add(t)));
    tagPool.forEach((t) => tags.add(t));
    return Array.from(tags).sort();
  }, [documents, tagPool]);

  const availableAuthors = useMemo(() => {
    return Array.from(new Set(documents.map((d) => d.author)));
  }, [documents]);

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      if (filters.searchText) {
        const q = filters.searchText.toLowerCase();
        const haystack = [
          doc.name,
          doc.author,
          doc.vendor ?? "",
          doc.documentType ?? "",
          doc.project ?? "",
          ...(doc.tags ?? []),
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }

      if (filters.selectedTags.length) {
        const match =
          filters.tagMatchMode === "all"
            ? filters.selectedTags.every((t) => doc.tags.includes(t))
            : filters.selectedTags.some((t) => doc.tags.includes(t));
        if (!match) return false;
      }

      if (filters.author && doc.author !== filters.author) return false;

      if (filters.dateRange) {
        const docDate = doc.date ? new Date(`${doc.date}T00:00:00`) : null;
        if (!docDate || Number.isNaN(docDate.getTime())) return false;

        const today = new Date();
        const now = new Date(
          today.getFullYear(),
          today.getMonth(),
          today.getDate(),
        );

        if (filters.dateRange === "today") {
          if (docDate.getTime() !== now.getTime()) return false;
        } else if (filters.dateRange === "week") {
          const weekStart = new Date(now);
          weekStart.setDate(now.getDate() - now.getDay());
          if (docDate < weekStart || docDate > now) return false;
        } else if (filters.dateRange === "month") {
          if (
            docDate.getFullYear() !== now.getFullYear() ||
            docDate.getMonth() !== now.getMonth()
          ) {
            return false;
          }
        } else if (filters.dateRange === "quarter") {
          const currentQuarter = Math.floor(now.getMonth() / 3);
          const docQuarter = Math.floor(docDate.getMonth() / 3);
          if (
            docDate.getFullYear() !== now.getFullYear() ||
            docQuarter !== currentQuarter
          ) {
            return false;
          }
        } else if (filters.dateRange === "year") {
          if (docDate.getFullYear() !== now.getFullYear()) return false;
        } else if (filters.dateRange === "custom") {
          if (!filters.startDate || !filters.endDate) return false;

          const start = new Date(
            filters.startDate.getFullYear(),
            filters.startDate.getMonth(),
            filters.startDate.getDate(),
          );
          const end = new Date(
            filters.endDate.getFullYear(),
            filters.endDate.getMonth(),
            filters.endDate.getDate(),
          );

          if (docDate < start || docDate > end) return false;
        }
      }

      return true;
    });
  }, [documents, filters]);

  const workspaceDocuments = useMemo(
    () => filteredDocuments.filter((doc) => doc.inWorkspace),
    [filteredDocuments],
  );

  useEffect(() => {
    if (!documents.length && !searchTextRef.current) return;

    const timeoutId = window.setTimeout(() => {
      refreshDocuments().catch(() => toast.error("Failed to load documents"));
    }, 250);

    return () => window.clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.searchText]);

  /**
   * Actions
   */
  // const handleUpload = async (files: File[]) => {
  //   let successCount = 0;
  //   let failureCount = 0;

  //   for (const file of files) {
  //     try {
  //       await uploadDocument(file);
  //       successCount++;
  //     } catch (err: any) {
  //       failureCount++;

  //       // Optional: surface duplicate vs generic error
  //       if (err?.status === 409) {
  //         toast.error(`Duplicate file: ${file.name}`);
  //       } else {
  //         toast.error(`Failed to upload ${file.name}`);
  //       }

  //       // IMPORTANT: continue loop, do NOT throw
  //     }
  //   }

  //   if (successCount && !failureCount) {
  //     toast(
  //       <div className="flex items-center gap-3">
  //         <CheckCircle2 className="w-5 h-5 text-green-600" />
  //         <span>{successCount} file(s) uploaded</span>
  //       </div>
  //     );
  //   } else if (successCount && failureCount) {
  //     toast(
  //       <div className="flex items-center gap-3">
  //         <AlertTriangle className="w-5 h-5 text-yellow-600" />
  //         <span>
  //           {successCount} uploaded, {failureCount} failed
  //         </span>
  //       </div>
  //     );
  //   }
  // };

  const handleFileUpload = async (file: File) => {
    const loadingToastId = toast.loading(`Uploading ${file.name}...`);
    try {
      const uploaded = (await uploadDocument(file)) as { id?: string };

      // wait until backend actually returns the file
      const docs = await waitForDocument(file.name);

      if (docs) {
        setDocuments(docs.map(mapApiDocument));
      } else {
        // fallback if timing fails
        await refreshDocuments();
      }

      if (uploaded.id) {
        void pollDocumentStatus(uploaded.id);
      }

      // refresh supporting data without failing the upload toast if one panel is unavailable
      await Promise.allSettled([refreshTagPool(), refreshDuePayments()]);
      toast.success(`${file.name} uploaded`);
    } catch (error) {
      toast.error(`Failed to upload ${file.name}`);
      throw error;
    } finally {
      toast.dismiss(loadingToastId);
    }
  };

  const handleDelete = (doc: Document) => {
    // Remove from UI immediately
    setDocuments((prev) => prev.filter((d) => d.id !== doc.id));

    // Schedule backend delete
    const timeoutId = setTimeout(async () => {
      try {
        await deleteDocument(doc.id);
        setDeletedQueue((prev) =>
          prev.filter((item) => item.doc.id !== doc.id),
        );
      } catch {
        toast.error(`Failed to delete ${doc.name}`);
        await refreshDocuments();
      }
    }, 5000);

    // Add to deleted queue
    setDeletedQueue((prev) => [...prev, { doc, timeoutId }]);

    // Show toast with Undo button
    const toastId = toast(
      <div className="flex items-center gap-4">
        <span>{doc.name} deleted</span>
        <button
          className="underline text-blue-600"
          onClick={() => {
            clearTimeout(timeoutId); // cancel backend delete
            setDocuments((prev) => [...prev, doc]); // restore UI
            setDeletedQueue((prev) =>
              prev.filter((item) => item.doc.id !== doc.id),
            );
            toast.dismiss(toastId);
          }}
        >
          Undo
        </button>
      </div>,
      { duration: 5000 },
    );
  };

  // const handleBulkDelete = async () => {
  //   const docsToDelete = Array.from(selection.selected.values());

  //   docsToDelete.forEach((doc) => {
  //     // Remove from UI
  //     setDocuments((prev) => prev.filter((d) => d.id !== doc.id));

  //     const timeoutId = setTimeout(async () => {
  //       try {
  //         await deleteDocument(doc.id);
  //         setDeletedQueue((prev) => prev.filter((item) => item.doc.id !== doc.id));
  //       } catch {
  //         toast.error(`Failed to delete ${doc.name}`);
  //         await refreshDocuments();
  //       }
  //     }, 5000);

  //     setDeletedQueue((prev) => [...prev, { doc, timeoutId }]);

  //     const toastId = toast(
  //       <div className="flex items-center gap-4">
  //         <span>{doc.name} deleted</span>
  //         <button
  //           className="underline text-blue-600"
  //           onClick={() => {
  //             clearTimeout(timeoutId);
  //             setDocuments((prev) => [...prev, doc]);
  //             setDeletedQueue((prev) => prev.filter((item) => item.doc.id !== doc.id));
  //             toast.dismiss(toastId);
  //           }}
  //         >
  //           Undo
  //         </button>
  //       </div>,
  //       { duration: 5000 }
  //     );
  //   });

  //   selection.clear();
  // };

  const handlePreview = (doc: Document) => {
    const token = sessionStorage.getItem("access_token");
    const previewWindow = openLoadingPreviewWindow(doc.name);
    if (!previewWindow) {
      toast.error("Popup blocked");
      return;
    }

    fetch(`${API_BASE_URL}/documents/${doc.id}/preview`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
      .then(async (res) => {
        if (res.status === 401) {
          sessionStorage.removeItem("access_token");
          previewWindow.fail();
          window.location.reload();
          return;
        }
        if (!res.ok) throw new Error("Preview failed");
        if (isOfficeFilename(doc.name)) {
          previewWindow.finish(await res.text());
          return;
        }
        previewWindow.finish(await res.blob());
      })
      .catch(() => {
        previewWindow.fail();
        toast.error("Preview failed");
      });
  };

  const handlePreviewById = (documentId: string) => {
    const doc = documents.find((item) => item.id === documentId);
    if (doc) {
      handlePreview(doc);
      return;
    }
    toast.error("Document not found for preview");
  };

  const handleDownload = async (doc: Document) => {
    const token = sessionStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/documents/${doc.id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (res.status === 401) {
      sessionStorage.removeItem("access_token");
      window.location.reload();
      return;
    }
    if (!res.ok) {
      toast.error("Download failed");
      return;
    }

    await saveResponseAsFile(res, doc.name);
  };

  const handleReprocess = async (doc: Document) => {
    try {
      await reprocessDocument(doc.id);
      toast.success(`Reprocessing started for ${doc.name}`);
      await refreshDocuments();
      await refreshTagPool();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : `Failed to reprocess ${doc.name}`,
      );
    }
  };

  const handleBulkDownload = async () => {
    const selectedDocs = Array.from(selection.selected.values());
    if (!selectedDocs.length) return;

    try {
      const blob = await bulkDownloadDocuments(
        selectedDocs.map((doc) => doc.id),
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documents-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Bulk download failed",
      );
    }
  };

  const handleBulkReprocess = async () => {
    const selectedDocs = Array.from(selection.selected.values());
    if (!selectedDocs.length) return;

    const results = await Promise.allSettled(
      selectedDocs.map((doc) => reprocessDocument(doc.id)),
    );
    const successCount = results.filter((result) => result.status === "fulfilled").length;
    const failureCount = results.length - successCount;

    if (successCount > 0 && failureCount === 0) {
      toast.success(`Reprocessing started for ${successCount} document(s)`);
    } else if (successCount > 0) {
      toast.error(
        `Reprocessing started for ${successCount} document(s), failed for ${failureCount}`,
      );
    } else {
      toast.error("Failed to start reprocessing for selected documents");
    }

    await refreshDocuments();
    await refreshTagPool();
  };

  const handleBulkAddTags = async (tags: string[]) => {
    const selectedDocs = Array.from(selection.selected.values());
    const results = await Promise.allSettled(
      selectedDocs
        .filter((doc) => doc.currentVersionId)
        .map((doc) =>
          addDocumentVersionTags(doc.id, doc.currentVersionId!, tags),
        ),
    );
    const successCount = results.filter((r) => r.status === "fulfilled").length;
    const failCount = results.length - successCount;

    await refreshDocuments();
    await refreshTagPool();

    if (failCount === 0) {
      toast.success(`Added ${tags.length} tag(s) to ${successCount} document(s)`);
    } else {
      toast.error(`Added to ${successCount}, failed for ${failCount} document(s)`);
    }
  };

  const handleBulkRemoveTags = async (tags: string[]) => {
    const selectedDocs = Array.from(selection.selected.values());
    const results = await Promise.allSettled(
      selectedDocs
        .filter((doc) => doc.currentVersionId)
        .map((doc) =>
          removeDocumentVersionTags(doc.id, doc.currentVersionId!, tags),
        ),
    );
    const successCount = results.filter((r) => r.status === "fulfilled").length;
    const failCount = results.length - successCount;

    await refreshDocuments();
    await refreshTagPool();

    if (failCount === 0) {
      toast.success(`Removed ${tags.length} tag(s) from ${successCount} document(s)`);
    } else {
      toast.error(`Removed from ${successCount}, failed for ${failCount} document(s)`);
    }
  };

  const handleBulkSetWorkflow = async (
    status: "failed" | "uploaded" | "needs review",
  ) => {
    const selectedDocs = Array.from(selection.selected.values());
    const results = await Promise.allSettled(
      selectedDocs.map((doc) =>
        updateDocumentWorkflow(doc.id, { status, notes: "" }),
      ),
    );
    const successCount = results.filter((r) => r.status === "fulfilled").length;
    const failCount = results.length - successCount;

    // Optimistically update UI for succeeded docs; a full refresh would
    // overwrite notes fields so we only patch the workflow status locally.
    setDocuments((prev) =>
      prev.map((doc) =>
        selection.selected.has(doc.id)
          ? { ...doc, workflow: normalizeWorkflowStatus(status) }
          : doc,
      ),
    );

    if (failCount === 0) {
      toast.success(`Workflow set to "${status}" for ${successCount} document(s)`);
    } else {
      toast.error(`Updated ${successCount}, failed for ${failCount} document(s)`);
    }
  };

  const handleBulkMoveProject = async (projectName: string) => {
    const selectedDocs = Array.from(selection.selected.values());
    const results = await Promise.allSettled(
      selectedDocs.map((doc) => moveDocumentProject(doc.id, projectName)),
    );
    const successCount = results.filter((r) => r.status === "fulfilled").length;
    const failCount = results.length - successCount;

    await refreshDocuments();

    if (failCount === 0) {
      toast.success(`Moved ${successCount} document(s) to project: ${projectName}`);
    } else {
      toast.error(`Moved ${successCount}, failed for ${failCount} document(s)`);
    }

    selection.clear();
  };

  const handleEditWorkflow = (doc: Document) => {
    setSelectedDocument(doc);
    setWorkflowEditorOpen(true);
  };

  const handleSaveWorkflow = async (
    documentId: string,
    workflow: "failed" | "uploaded" | "needs review",
    notes: string,
  ) => {
    const response = await updateDocumentWorkflow(documentId, {
      status: workflow,
      notes,
    });
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === documentId
          ? {
              ...doc,
              workflow: normalizeWorkflowStatus(response.status),
              workflowNotes: response.notes,
            }
          : doc,
      ),
    );
    setSelectedDocument((prev) =>
      prev && prev.id === documentId
        ? {
            ...prev,
            workflow: normalizeWorkflowStatus(response.status),
            workflowNotes: response.notes,
          }
        : prev,
    );
    toast.success("Workflow updated");
  };

  const handleWorkspaceToggle = async (doc: Document) => {
    const next = !doc.inWorkspace;
    setDocuments((prev) =>
      prev.map((item) =>
        item.id === doc.id ? { ...item, inWorkspace: next } : item,
      ),
    );
    try {
      await updateDocumentWorkspace(doc.id, next);
    } catch (error) {
      setDocuments((prev) =>
        prev.map((item) =>
          item.id === doc.id ? { ...item, inWorkspace: !next } : item,
        ),
      );
      toast.error(
        error instanceof Error ? error.message : "Failed to update workspace flag",
      );
    }
  };

  const handleMoveProject = async (doc: Document, projectName: string) => {
    if (!accessPermissions.has("document.project_move")) {
      toast.error("You do not have permission to move projects");
      return;
    }
    try {
      const response = await moveDocumentProject(doc.id, projectName.trim());
      setDocuments((prev) =>
        prev.map((item) =>
          item.id === doc.id ? { ...item, tags: response.tags } : item,
        ),
      );
      toast.success(`Moved to project: ${response.project_tag}`);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to move project",
      );
    }
  };

  const handleCreateStandaloneTag = async (rawTag: string) => {
    const result = await createTagPool(rawTag);
    setTagPool((prev) => Array.from(new Set([...prev, result.tag])).sort());
    toast.success(`Tag created: ${result.tag}`);
  };

  const handleDeletePoolTag = async (tag: string) => {
    if (!accessPermissions.has("tags.delete") && !accessPermissions.has("tags.edit")) {
      toast.error("You do not have permission to delete tags from pool");
      return;
    }
    await deleteTagPool(tag);
    setTagPool((prev) => prev.filter((t) => t !== tag));
    setDocuments((prev) =>
      prev.map((doc) => ({
        ...doc,
        tags: doc.tags.filter((t) => t !== tag),
      })),
    );
    toast.success(`Tag removed from pool: ${tag}`);
  };

  const handleSaveDocumentTags = async (payload: {
    tags: string[];
    dueDate: string | null;
  }) => {
    if (!editingTagsDoc) return;
    if (!editingTagsDoc.currentVersionId) {
      toast.error("Document has no current version to tag");
      return;
    }
    const createCalls = payload.tags.map((tag) =>
      createTagPool(tag).catch(() => null),
    );
    await Promise.all(createCalls);
    const response = await replaceDocumentVersionTags(
      editingTagsDoc.id,
      editingTagsDoc.currentVersionId,
      payload.tags,
    );
    await updateDocumentVersionDueDate(
      editingTagsDoc.id,
      editingTagsDoc.currentVersionId,
      payload.dueDate,
    );

    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === editingTagsDoc.id
          ? { ...doc, tags: response.tags ?? [], dueDate: payload.dueDate }
          : doc,
      ),
    );
    if (editingTagsDoc.id === selectedDocument?.id) {
      setSelectedDocument((prev) =>
        prev ? { ...prev, tags: response.tags ?? [], dueDate: payload.dueDate } : prev,
      );
    }
    await refreshTagPool();
    await refreshDuePayments();
    toast.success("Document details updated");
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div
        className={`flex min-h-screen w-full overflow-x-hidden ${darkMode ? "bg-gray-900 text-white" : ""}`}
      >
        <div className="hidden shrink-0 lg:block">
          <SearchFilters
            filters={filters}
            onFiltersChange={setFilters}
            availableTags={availableTags}
            availableAuthors={availableAuthors}
            onCreateTag={handleCreateStandaloneTag}
            onDeleteTagFromPool={handleDeletePoolTag}
            canDeleteTagFromPool={
              accessPermissions.has("tags.delete") ||
              accessPermissions.has("tags.edit")
            }
            darkMode={darkMode}
            variant="sidebar"
          />
        </div>

        <Drawer open={filtersOpen} onOpenChange={setFiltersOpen} direction="left">
          <DrawerContent className="p-0">
            <SearchFilters
              filters={filters}
              onFiltersChange={setFilters}
              availableTags={availableTags}
              availableAuthors={availableAuthors}
              onCreateTag={handleCreateStandaloneTag}
              onDeleteTagFromPool={handleDeletePoolTag}
              canDeleteTagFromPool={
                accessPermissions.has("tags.delete") ||
                accessPermissions.has("tags.edit")
              }
              darkMode={darkMode}
              variant="drawer"
            />
          </DrawerContent>
        </Drawer>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Header */}
          <div className="border-b px-4 py-4 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-blue-600" />
                <div>
                  <h1 className="text-2xl">Document Management System</h1>
                  <p className="text-sm text-gray-500">
                    {filteredDocuments.length} document(s)
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  className="lg:hidden"
                  onClick={() => setFiltersOpen(true)}
                >
                  <SlidersHorizontal className="mr-2 h-4 w-4" />
                  Show Filters
                </Button>
                <Button
                  variant={viewMode === "compact" ? "default" : "outline"}
                  onClick={() => setViewMode("compact")}
                >
                  <AlignJustify className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === "grouped" ? "default" : "outline"}
                  onClick={() => setViewMode("grouped")}
                >
                  <Layers className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setDarkMode(!darkMode)}
                >
                  {darkMode ? <Sun /> : <Moon />}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setLiveSyncEnabled((prev) => !prev)}
                >
                  {liveSyncEnabled ? "Live Sync On" : "Live Sync Off"}
                </Button>
                <div
                  className={`mx-1 h-5 w-px ${darkMode ? "bg-gray-600" : "bg-gray-300"}`}
                />
                {isAdmin && (
                  <Button
                    variant="outline"
                    onClick={() => setActiveTab("admin")}
                  >
                    <Shield className="mr-2 h-4 w-4" />
                    Admin
                  </Button>
                )}
                <Button variant="outline" onClick={() => setProfileOpen(true)}>
                  <UserCircle2 className="mr-2 h-4 w-4" />
                  Profile
                </Button>
                <Button variant="outline" onClick={handleLogout}>
                  Log out
                </Button>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-x-hidden overflow-y-auto px-4 py-4 pb-24 sm:px-6">
            <div className="flex min-w-0 flex-col gap-6 lg:flex-row lg:items-start">
              <div className="min-w-0 flex-1">
                <Tabs
                  value={activeTab}
                  onValueChange={(value) =>
                    setActiveTab(value as "documents" | "workspace" | "upload" | "admin")
                  }
                >
                  <TabsList className="w-full flex-wrap sm:w-fit">
                    <TabsTrigger value="documents">
                      <FileText className="w-4 h-4 mr-2" />
                      Documents
                    </TabsTrigger>
                    <TabsTrigger value="workspace">
                      <Bookmark className="w-4 h-4 mr-2" />
                      Workspace
                    </TabsTrigger>
                    <TabsTrigger value="upload">
                      <UploadIcon className="w-4 h-4 mr-2" />
                      Upload
                    </TabsTrigger>
                  </TabsList>

                  <BulkActionBar
                    count={selection.selected.size}
                    darkMode={darkMode}
                    availableTags={availableTags}
                    canDelete={accessPermissions.has("document.delete")}
                    onDownload={() => {
                      void handleBulkDownload();
                    }}
                    onReprocess={() => {
                      void handleBulkReprocess();
                    }}
                    onDelete={async () => {
                      for (const doc of selection.selected.values()) {
                        await handleDelete(doc);
                      }
                      selection.clear();
                    }}
                    onClear={selection.clear}
                    onBulkAddTags={handleBulkAddTags}
                    onBulkRemoveTags={handleBulkRemoveTags}
                    onBulkSetWorkflow={handleBulkSetWorkflow}
                    onBulkMoveProject={handleBulkMoveProject}
                    documents={[]}
                  />

                  <TabsContent value="documents" className="mt-6">
                    {viewMode === "compact" ? (
                      <CompactProjectView
                        documents={filteredDocuments}
                        onPreview={handlePreview}
                        onDownload={handleDownload}
                        onDelete={handleDelete}
                        onEditWorkflow={handleEditWorkflow}
                        onEditTags={(doc) => setEditingTagsDoc(doc)}
                        onMoveProject={
                          accessPermissions.has("document.project_move")
                            ? handleMoveProject
                            : undefined
                        }
                        onReprocess={handleReprocess}
                        onOpenVersions={(doc) => setVersionModalDoc(doc)}
                        onToggleWorkspace={handleWorkspaceToggle}
                        availableTags={availableTags}
                        darkMode={darkMode}
                      />
                    ) : viewMode === "grouped" ? (
                      <GroupedDocuments
                        documents={filteredDocuments}
                        onPreview={handlePreview}
                        onDownload={handleDownload}
                        onDelete={handleDelete}
                        onEditWorkflow={handleEditWorkflow}
                        onEditTags={(doc) => setEditingTagsDoc(doc)}
                        onMoveProject={
                          accessPermissions.has("document.project_move")
                            ? handleMoveProject
                            : undefined
                        }
                        onReprocess={handleReprocess}
                        onToggleWorkspace={handleWorkspaceToggle}
                        darkMode={darkMode}
                      />
                    ) : (
                      <div className="grid gap-4">
                        {filteredDocuments.map((doc) => (
                          <DocumentCard
                            key={doc.id}
                            document={doc}
                            onPreview={() => handlePreview(doc)}
                            onDownload={() => handleDownload(doc)}
                            onDelete={() => handleDelete(doc)}
                            onEditWorkflow={() => handleEditWorkflow(doc)}
                            onEditTags={() => setEditingTagsDoc(doc)}
                            onMoveProject={
                              accessPermissions.has("document.project_move")
                                ? () => handleMoveProject(doc)
                                : undefined
                            }
                          />
                        ))}
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="workspace" className="mt-6">
                    <CompactProjectView
                      documents={workspaceDocuments}
                      onPreview={handlePreview}
                      onDownload={handleDownload}
                      onDelete={handleDelete}
                      onEditWorkflow={handleEditWorkflow}
                      onEditTags={(doc) => setEditingTagsDoc(doc)}
                      onMoveProject={
                        accessPermissions.has("document.project_move")
                          ? handleMoveProject
                          : undefined
                      }
                      onReprocess={handleReprocess}
                      onOpenVersions={(doc) => setVersionModalDoc(doc)}
                      onToggleWorkspace={handleWorkspaceToggle}
                      availableTags={availableTags}
                      darkMode={darkMode}
                    />
                  </TabsContent>

                  <TabsContent value="upload" className="mt-6">
                    <UploadZone
                      onFileUploaded={handleFileUpload}
                      darkMode={darkMode}
                    />
                  </TabsContent>

                  {isAdmin && (
                    <TabsContent value="admin" className="mt-6">
                      <RolesPage
                        darkMode={darkMode}
                        onBackToDocuments={() => setActiveTab("documents")}
                      />
                    </TabsContent>
                  )}
                </Tabs>
              </div>

              {activeTab === "documents" && (
                <div className="w-full lg:w-80 lg:shrink-0">
                  <div className="lg:sticky lg:top-6">
                    <UpcomingDuePaymentsPanel
                      items={duePayments}
                      loading={duePaymentsLoading}
                      darkMode={darkMode}
                      onPreview={(item) => handlePreviewById(item.documentId)}
                      daysAhead={duePaymentsWindowDays}
                      onDaysAheadChange={setDuePaymentsWindowDays}
                      hasAccess={accessPermissions.has("document.due_payments")}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <WorkflowEditor
            document={selectedDocument}
            open={workflowEditorOpen}
            onOpenChange={setWorkflowEditorOpen}
            onSave={handleSaveWorkflow}
          />

          <VersionHistoryModal
            open={versionModalDoc !== null}
            document={versionModalDoc}
            onClose={() => setVersionModalDoc(null)}
            onUpdated={refreshDocuments}
            darkMode={darkMode}
          />

          <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
          <TagEditorDialog
            open={editingTagsDoc !== null}
            document={editingTagsDoc}
            availableTags={availableTags}
            onOpenChange={(open) => {
              if (!open) setEditingTagsDoc(null);
            }}
            onSave={handleSaveDocumentTags}
            darkMode={darkMode}
          />

          <Toaster />
        </div>
      </div>
    </DndProvider>
  );
}

export default function App() {
  return (
    <SelectionProvider>
      <AppInner />
    </SelectionProvider>
  );
}