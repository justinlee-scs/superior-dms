import { useState, useMemo, useEffect } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";

import { DocumentCard, type Document } from "@/app/components/document-card";
import { GroupedDocuments } from "@/app/components/grouped-documents";
import { CompactProjectView } from "@/app/components/compact-project-view";
import { SearchFilters, type FilterState } from "@/app/components/search-filters";
import { UploadZone } from "@/app/components/upload-zone";
import { WorkflowEditor } from "@/app/components/workflow-editor";
import { BulkActionBar } from "@/app/components/bulk-action-bar";
import { VersionHistoryModal } from "@/app/components/version-history-modal";
import { ProfileDialog } from "@/app/components/profile-dialog";
import { TagEditorDialog } from "@/app/components/tag-editor-dialog";

import { SelectionProvider, useSelection } from "@/app/selection/selection-context";

import { Button } from "@/app/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs";
import { Toaster } from "@/app/components/ui/sonner";

import {
  FileText,
  Upload as UploadIcon,
  Layers,
  AlignJustify,
  Moon,
  Sun,
  CheckCircle2,
  AlertTriangle,
  Shield,
  UserCircle2
} from "lucide-react";

import { toast } from "sonner";
import {
  bulkDownloadDocuments,
  createTagPool,
  deleteDocument,
  listDocuments,
  listTagPool,
  replaceDocumentVersionTags,
  uploadDocument,
} from "@/lib/dms";
import { API_BASE_URL } from "@/lib/api";
import { getMyAccess } from "@/lib/rbac";
import RolesPage from "@/admin/roles-page";

/**
 * Maps backend document → UI Document
 */
function mapApiDocument(doc: any): Document {
  const extension = (doc.filename?.split(".").pop() ?? "file").toLowerCase();
  return {
    id: doc.id,
    name: doc.filename,
    type: extension,
    size: doc.size ?? "—",
    author: doc.author ?? "System",
    date: doc.created_at?.slice(0, 10) ?? "",
    tags: doc.tags ?? [],
    workflow: doc.status ?? "uploaded",
    project: doc.project ?? "Default",
    documentType: doc.document_type ?? "Document",
    vendor: doc.vendor,
    projectNumber: doc.project_number,
    currentVersionId: doc.current_version_id,
    currentVersionNumber: doc.current_version_number ?? 1,
    versionCount: doc.version_count ?? 1,
  };
}

function AppInner() {
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

  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [workflowEditorOpen, setWorkflowEditorOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"compact" | "grouped">("compact");
  const [darkMode, setDarkMode] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [versionModalDoc, setVersionModalDoc] = useState<Document | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"documents" | "upload" | "admin">("documents");
  const [tagPool, setTagPool] = useState<string[]>([]);
  const [editingTagsDoc, setEditingTagsDoc] = useState<Document | null>(null);

  const selection = useSelection();

  /**
   * Load documents
   */
  const refreshDocuments = async () => {
    const apiDocs = await listDocuments() as any[];
    const baseDocs = apiDocs.map(mapApiDocument);
    setDocuments(baseDocs);
  };

  const refreshTagPool = async () => {
    const data = await listTagPool();
    setTagPool(data.tags ?? []);
  };

  useEffect(() => {
    refreshDocuments().catch(() =>
      toast.error("Failed to load documents")
    );
    refreshTagPool().catch(() => toast.error("Failed to load tags"));
  }, []);

  useEffect(() => {
    getMyAccess()
      .then((access) => {
        const hasAdminUsers = access.permissions.includes("admin.users");
        const hasAdminRoles = access.permissions.includes("admin.roles");
        setIsAdmin(hasAdminUsers || hasAdminRoles);
      })
      .catch(() => {
        setIsAdmin(false);
      });
  }, []);

  useEffect(() => {
    refreshDocuments().catch(() => toast.error("Failed to load documents"));
    refreshTagPool().catch(() => toast.error("Failed to load tags"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        if (!doc.name.toLowerCase().includes(q)) return false;
      }

      if (filters.selectedTags.length) {
        const match =
          filters.tagMatchMode === "all"
            ? filters.selectedTags.every((t) => doc.tags.includes(t))
            : filters.selectedTags.some((t) => doc.tags.includes(t));
        if (!match) return false;
      }

      if (filters.author && doc.author !== filters.author) return false;

      return true;
    });
  }, [documents, filters]);

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
    await uploadDocument(file); // MUST throw on failure
  };

  const handleDelete = (doc: Document) => {
    // Remove from UI immediately
    setDocuments((prev) => prev.filter((d) => d.id !== doc.id));

    // Schedule backend delete
    const timeoutId = setTimeout(async () => {
      try {
        await deleteDocument(doc.id);
        setDeletedQueue((prev) => prev.filter((item) => item.doc.id !== doc.id));
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
            setDeletedQueue((prev) => prev.filter((item) => item.doc.id !== doc.id));
            toast.dismiss(toastId);
          }}
        >
          Undo
        </button>
      </div>,
      { duration: 5000 }
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
    fetch(`${API_BASE_URL}/documents/${doc.id}/preview`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("Preview failed");
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        window.open(url, "_blank");
      })
      .catch(() => toast.error("Preview failed"));
  };

  const handleDownload = async (doc: Document) => {
    const token = sessionStorage.getItem("access_token");
    const res = await fetch(`${API_BASE_URL}/documents/${doc.id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!res.ok) {
      toast.error("Download failed");
      return;
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleBulkDownload = async () => {
    const selectedDocs = Array.from(selection.selected.values());
    if (!selectedDocs.length) return;

    try {
      const blob = await bulkDownloadDocuments(selectedDocs.map((doc) => doc.id));
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `documents-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Bulk download failed");
    }
  };

  const handleEditWorkflow = (doc: Document) => {
    setSelectedDocument(doc);
    setWorkflowEditorOpen(true);
  };

  const handleCreateStandaloneTag = async (rawTag: string) => {
    const result = await createTagPool(rawTag);
    setTagPool((prev) => Array.from(new Set([...prev, result.tag])).sort());
    toast.success(`Tag created: ${result.tag}`);
  };

  const handleSaveDocumentTags = async (nextTags: string[]) => {
    if (!editingTagsDoc) return;
    if (!editingTagsDoc.currentVersionId) {
      toast.error("Document has no current version to tag");
      return;
    }
    const createCalls = nextTags.map((tag) => createTagPool(tag).catch(() => null));
    await Promise.all(createCalls);
    const response = await replaceDocumentVersionTags(
      editingTagsDoc.id,
      editingTagsDoc.currentVersionId,
      nextTags,
    );

    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === editingTagsDoc.id ? { ...doc, tags: response.tags ?? [] } : doc,
      ),
    );
    await refreshTagPool();
    toast.success("Document tags updated");
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className={`flex h-screen ${darkMode ? "bg-gray-900 text-white" : ""}`}>
        <SearchFilters
          filters={filters}
          onFiltersChange={setFilters}
          availableTags={availableTags}
          availableAuthors={availableAuthors}
          onCreateTag={handleCreateStandaloneTag}
          darkMode={darkMode}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="border-b p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-blue-600" />
                <div>
                  <h1 className="text-2xl">Document Management System</h1>
                  <p className="text-sm text-gray-500">
                    {filteredDocuments.length} document(s)
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
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
                <Button variant="outline" onClick={() => setDarkMode(!darkMode)}>
                  {darkMode ? <Sun /> : <Moon />}
                </Button>
                <div className={`mx-1 h-5 w-px ${darkMode ? "bg-gray-600" : "bg-gray-300"}`} />
                {isAdmin && (
                  <Button variant="outline" onClick={() => setActiveTab("admin")}>
                    <Shield className="mr-2 h-4 w-4" />
                    Admin
                  </Button>
                )}
                <Button variant="outline" onClick={() => setProfileOpen(true)}>
                  <UserCircle2 className="mr-2 h-4 w-4" />
                  Profile
                </Button>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-6 pb-24">
            <Tabs
              value={activeTab}
              onValueChange={(value) => setActiveTab(value as "documents" | "upload" | "admin")}
            >
              <TabsList>
                <TabsTrigger value="documents">
                  <FileText className="w-4 h-4 mr-2" />
                  Documents
                </TabsTrigger>
                <TabsTrigger value="upload">
                  <UploadIcon className="w-4 h-4 mr-2" />
                  Upload
                </TabsTrigger>
              </TabsList>

              <BulkActionBar
                count={selection.selected.size}
                darkMode={darkMode}
                onDownload={() => {
                  void handleBulkDownload();
                } }
                onDelete={async () => {
                  for (const doc of selection.selected.values()) {
                    await handleDelete(doc);
                  }
                  selection.clear();
                } }
                onClear={selection.clear} documents={[]}              />

              <TabsContent value="documents" className="mt-6">
                {viewMode === "compact" ? (
                  <CompactProjectView
                    documents={filteredDocuments}
                    onPreview={handlePreview}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                    onEditWorkflow={handleEditWorkflow}
                    onEditTags={(doc) => setEditingTagsDoc(doc)}
                    onOpenVersions={(doc) => setVersionModalDoc(doc)}
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
                      />
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="upload" className="mt-6">
                {/* <UploadZone onFilesUploaded={handleUpload} /> */}
                <UploadZone 
                onFileUploaded={handleFileUpload}
                darkMode={darkMode}
                 />
              </TabsContent>

              {isAdmin && (
                <TabsContent value="admin" className="mt-6">
                  <RolesPage darkMode={darkMode} onBackToDocuments={() => setActiveTab("documents")} />
                </TabsContent>
              )}
            </Tabs>
          </div>



          <WorkflowEditor
            document={selectedDocument}
            open={workflowEditorOpen}
            onOpenChange={setWorkflowEditorOpen}
            onSave={() => { }}
          />

          <VersionHistoryModal
            open={versionModalDoc !== null}
            document={versionModalDoc}
            onClose={() => setVersionModalDoc(null)}
            onUpdated={refreshDocuments}
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
