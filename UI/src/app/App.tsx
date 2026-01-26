import { useState, useMemo, useEffect } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";

import { DocumentCard, type Document } from "@/app/components/document-card";
import { GroupedDocuments } from "@/app/components/grouped-documents";
import { CompactProjectView } from "@/app/components/compact-project-view";
import { SearchFilters, type FilterState } from "@/app/components/search-filters";
import { UploadZone } from "@/app/components/upload-zone";
import { WorkflowEditor } from "@/app/components/workflow-editor";

import { Button } from "@/app/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs";
import { Toaster } from "@/app/components/ui/sonner";

import {
  FileText,
  Upload as UploadIcon,
  Grid3x3,
  List,
  Layers,
  AlignJustify,
  Moon,
  Sun,
  UserCircle,
} from "lucide-react";

import { toast } from "sonner";
import { listDocuments, uploadDocument, deleteDocument } from "@/lib/dms";
import { API_BASE_URL } from "@/lib/api";

/**
 * Maps backend document → UI Document
 */
function mapApiDocument(doc: any): Document {
  return {
    id: doc.id,
    name: doc.filename,
    type: doc.filename?.split(".").pop() ?? "file",
    size: doc.size ?? "—",
    author: doc.author ?? "System",
    date: doc.created_at?.slice(0, 10) ?? "",
    tags: doc.tags ?? [],
    workflow: doc.status ?? "uploaded",
    project: doc.project ?? "Default",
    documentType: doc.document_type ?? "Document",
    vendor: doc.vendor,
    projectNumber: doc.project_number,
  };
}

export default function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
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
  const [viewMode, setViewMode] =
    useState<"compact" | "grid" | "list" | "grouped">("compact");
  const [darkMode, setDarkMode] = useState(false);

  /**
   * Load documents from backend
   */
  const refreshDocuments = async () => {
    const apiDocs = await listDocuments();
    setDocuments(apiDocs.map(mapApiDocument));
  };

  useEffect(() => {
    refreshDocuments().catch(() =>
      toast.error("Failed to load documents")
    );
  }, []);

  /**
   * Filters
   */
  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    documents.forEach((d) => d.tags.forEach((t) => tags.add(t)));
    return Array.from(tags);
  }, [documents]);

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
  const handleUpload = async (files: File[]) => {
    for (const file of files) {
      await uploadDocument(file);
    }
    toast.success("Upload complete");
    await refreshDocuments();
  };

  const handleDelete = async (doc: Document) => {
    await deleteDocument(doc.id);
    toast.success("Document deleted");
    await refreshDocuments();
  };

  //   const handlePreview = async (doc: Document) => {
  //   try {
  //     const res = await fetch(`${API_BASE_URL}/documents/${doc.id}/download`);
  //     if (!res.ok) throw new Error("Preview failed");

  //     const blob = await res.blob();
  //     const url = window.URL.createObjectURL(blob);
  //     window.open(url, "_blank"); // Open file in new tab
  //     // Do not revoke URL immediately because tab still needs it
  //   } catch (err) {
  //     console.error(err);
  //     toast.error("Failed to preview file");
  //   }
  // };

  const handlePreview = (doc: Document) => {
    // Open a new tab with the download URL
    window.open(`http://127.0.0.1:8008/documents/${doc.id}/preview`, "_blank");
  };


  const handleDownload = async (doc: Document) => {
    try {
      const res = await fetch(`${API_BASE_URL}/documents/${doc.id}/download`);
      if (!res.ok) throw new Error("Download failed");

      const blob = await res.blob(); // Get file content as blob
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.name; // Suggest file name
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast.success("Downloading");
    } catch (err) {
      console.error(err);
      toast.error("Failed to download file");
    }
  };


  const handleEditWorkflow = (doc: Document) => {
    setSelectedDocument(doc);
    setWorkflowEditorOpen(true);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className={`flex h-screen ${darkMode ? "bg-gray-900 text-white" : ""}`}>
        <SearchFilters
          filters={filters}
          onFiltersChange={setFilters}
          availableTags={availableTags}
          availableAuthors={availableAuthors}
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

              <div className="flex gap-2">
                <Button
                  variant={viewMode === "compact" ? "default" : "outline"}
                  onClick={() => setViewMode("compact")}
                >
                  <AlignJustify className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === "grid" ? "default" : "outline"}
                  onClick={() => setViewMode("grid")}
                >
                  <Grid3x3 className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "outline"}
                  onClick={() => setViewMode("list")}
                >
                  <List className="w-4 h-4" />
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
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-6">
            <Tabs defaultValue="documents">
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

              <TabsContent value="documents" className="mt-6">
                {viewMode === "compact" ? (
                  <CompactProjectView
                    documents={filteredDocuments}
                    onPreview={handlePreview}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                    onEditWorkflow={handleEditWorkflow}
                    darkMode={darkMode}
                  />
                ) : viewMode === "grouped" ? (
                  <GroupedDocuments
                    documents={filteredDocuments}
                    onPreview={handlePreview}
                    onDownload={handleDownload}
                    onDelete={handleDelete}
                    onEditWorkflow={handleEditWorkflow}
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
                      />
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="upload" className="mt-6">
                <UploadZone onFilesUploaded={handleUpload} />
              </TabsContent>
            </Tabs>
          </div>
        </div>

        <WorkflowEditor
          document={selectedDocument}
          open={workflowEditorOpen}
          onOpenChange={setWorkflowEditorOpen}
          onSave={() => { }}
        />

        <Toaster />
      </div>
    </DndProvider>
  );
}
