import { useState, useMemo } from "react";
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
import { FileText, Upload as UploadIcon, Grid3x3, List, Layers, AlignJustify, Moon, Sun, UserCircle } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "@/app/components/ui/sonner";

// Mock data
const INITIAL_DOCUMENTS: Document[] = [
  {
    id: "1",
    name: "Q4 Financial Report.pdf",
    type: "pdf",
    size: "2.4 MB",
    author: "Sarah Johnson",
    date: "2026-01-10",
    tags: ["Finance", "Q4", "Report"],
    workflow: "Approved",
    project: "Phoenix Redesign",
    documentType: "Report",
    vendor: "Acme Financial Services",
    projectNumber: "PRJ-2024-001",
  },
  {
    id: "2",
    name: "Project Proposal.docx",
    type: "document",
    size: "856 KB",
    author: "Michael Chen",
    date: "2026-01-12",
    tags: ["Project", "Proposal", "Marketing"],
    workflow: "In Review",
    project: "Phoenix Redesign",
    documentType: "Proposal",
    vendor: "Phoenix Creative Agency",
    projectNumber: "PRJ-2024-001",
  },
  {
    id: "3",
    name: "Sales Data 2025.xlsx",
    type: "spreadsheet",
    size: "1.8 MB",
    author: "Emily Rodriguez",
    date: "2026-01-08",
    tags: ["Sales", "Data", "Analytics"],
    workflow: "Published",
    project: "Atlas Launch",
    documentType: "Statement",
    vendor: "DataCore Analytics",
    projectNumber: "PRJ-2025-042",
  },
  {
    id: "4",
    name: "Brand Guidelines.pdf",
    type: "pdf",
    size: "5.2 MB",
    author: "David Kim",
    date: "2026-01-05",
    tags: ["Brand", "Design", "Guidelines"],
    workflow: "Approved",
    project: "Phoenix Redesign",
    documentType: "Contract",
    vendor: "Phoenix Creative Agency",
    projectNumber: "PRJ-2024-001",
  },
  {
    id: "5",
    name: "Meeting Minutes.docx",
    type: "document",
    size: "124 KB",
    author: "Sarah Johnson",
    date: "2026-01-13",
    tags: ["Meeting", "Minutes"],
    workflow: "Draft",
    project: "Atlas Launch",
    documentType: "Report",
    projectNumber: "PRJ-2025-042",
  },
  {
    id: "6",
    name: "Product Roadmap.png",
    type: "image",
    size: "892 KB",
    author: "Michael Chen",
    date: "2026-01-11",
    tags: ["Product", "Roadmap", "Planning"],
    workflow: "Pending Approval",
    project: "Vertex Integration",
    documentType: "Proposal",
    vendor: "TechVision Solutions",
    projectNumber: "PRJ-2025-089",
  },
  {
    id: "7",
    name: "Customer Feedback Analysis.pdf",
    type: "pdf",
    size: "1.5 MB",
    author: "Emily Rodriguez",
    date: "2026-01-09",
    tags: ["Customer", "Feedback", "Analysis"],
    workflow: "In Review",
    project: "Atlas Launch",
    documentType: "Report",
    vendor: "InsightMetrics Inc",
    projectNumber: "PRJ-2025-042",
  },
  {
    id: "8",
    name: "Budget 2026.xlsx",
    type: "spreadsheet",
    size: "2.1 MB",
    author: "David Kim",
    date: "2026-01-07",
    tags: ["Budget", "Finance", "Planning"],
    workflow: "Draft",
    project: "Phoenix Redesign",
    documentType: "Statement",
    vendor: "Acme Financial Services",
    projectNumber: "PRJ-2024-001",
  },
  {
    id: "9",
    name: "User Research Summary.docx",
    type: "document",
    size: "654 KB",
    author: "Sarah Johnson",
    date: "2026-01-11",
    tags: ["Research", "UX", "Analysis"],
    workflow: "Approved",
    project: "Vertex Integration",
    documentType: "Report",
    vendor: "UserFirst Research",
    projectNumber: "PRJ-2025-089",
  },
  {
    id: "10",
    name: "Technical Specification.pdf",
    type: "pdf",
    size: "3.2 MB",
    author: "Michael Chen",
    date: "2026-01-09",
    tags: ["Technical", "Specification", "Engineering"],
    workflow: "In Review",
    project: "Vertex Integration",
    documentType: "Contract",
    vendor: "TechVision Solutions",
    projectNumber: "PRJ-2025-089",
  },
  {
    id: "11",
    name: "Marketing Assets.zip",
    type: "archive",
    size: "12.4 MB",
    author: "Emily Rodriguez",
    date: "2026-01-08",
    tags: ["Marketing", "Assets", "Creative"],
    workflow: "Published",
    project: "Atlas Launch",
    documentType: "Invoice",
    vendor: "CreativeEdge Media",
    projectNumber: "PRJ-2025-042",
  },
  {
    id: "12",
    name: "Design Mockups.png",
    type: "image",
    size: "4.1 MB",
    author: "David Kim",
    date: "2026-01-12",
    tags: ["Design", "Mockups", "UI"],
    workflow: "Pending Approval",
    project: "Phoenix Redesign",
    documentType: "Proposal",
    vendor: "Phoenix Creative Agency",
    projectNumber: "PRJ-2024-001",
  },
];

export default function App() {
  const [documents, setDocuments] = useState<Document[]>(INITIAL_DOCUMENTS);
  const [filters, setFilters] = useState<FilterState>({
    searchText: "",
    selectedTags: [],
    author: "",
    dateRange: "",
    startDate: undefined,
    endDate: undefined,
    tagMatchMode: "any", // Initialize with default value
  });
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [workflowEditorOpen, setWorkflowEditorOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"compact" | "grid" | "list" | "grouped">("compact");
  const [darkMode, setDarkMode] = useState(false);

  // Extract unique tags and authors
  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    documents.forEach((doc) => doc.tags.forEach((tag) => tags.add(tag)));
    return Array.from(tags).sort();
  }, [documents]);

  const availableAuthors = useMemo(() => {
    const authors = new Set(documents.map((doc) => doc.author));
    return Array.from(authors).sort();
  }, [documents]);

  // Filter documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      // Text search - searches across name, project, tags, vendor, project number, AND author
      // Supports multiple keywords: "atlas analysis" requires BOTH words to match
      if (filters.searchText) {
        const keywords = filters.searchText.toLowerCase().trim().split(/\s+/);
        
        // Each keyword must match at least one field
        const allKeywordsMatch = keywords.every(keyword => {
          const matchesName = doc.name.toLowerCase().includes(keyword);
          const matchesProject = doc.project.toLowerCase().includes(keyword);
          const matchesTags = doc.tags.some(tag => tag.toLowerCase().includes(keyword));
          const matchesVendor = doc.vendor?.toLowerCase().includes(keyword);
          const matchesProjectNumber = doc.projectNumber?.toLowerCase().includes(keyword);
          const matchesAuthor = doc.author.toLowerCase().includes(keyword);
          
          return matchesName || matchesProject || matchesTags || matchesVendor || matchesProjectNumber || matchesAuthor;
        });
        
        if (!allKeywordsMatch) {
          return false;
        }
      }

      // Tag filter - support both "any" and "all" matching modes
      if (filters.selectedTags.length > 0) {
        const tagMatchMode = filters.tagMatchMode || "any";
        
        if (tagMatchMode === "all") {
          // ALL mode: document must have ALL selected tags
          const hasAllTags = filters.selectedTags.every((tag) => doc.tags.includes(tag));
          if (!hasAllTags) {
            return false;
          }
        } else {
          // ANY mode: document must have at least one selected tag
          const hasAnyTag = filters.selectedTags.some((tag) => doc.tags.includes(tag));
          if (!hasAnyTag) {
            return false;
          }
        }
      }

      // Author filter (dropdown)
      if (filters.author && doc.author !== filters.author) {
        return false;
      }

      // Date filter - handle both preset ranges and custom date range
      if (filters.dateRange && filters.dateRange !== "custom") {
        const docDate = new Date(doc.date);
        const now = new Date();
        const diffDays = Math.floor(
          (now.getTime() - docDate.getTime()) / (1000 * 60 * 60 * 24)
        );

        switch (filters.dateRange) {
          case "today":
            if (diffDays > 0) return false;
            break;
          case "week":
            if (diffDays > 7) return false;
            break;
          case "month":
            if (diffDays > 30) return false;
            break;
          case "quarter":
            if (diffDays > 90) return false;
            break;
          case "year":
            if (diffDays > 365) return false;
            break;
        }
      }

      // Custom date range filter
      if (filters.startDate || filters.endDate) {
        const docDate = new Date(doc.date);
        
        if (filters.startDate) {
          const startOfDay = new Date(filters.startDate);
          startOfDay.setHours(0, 0, 0, 0);
          if (docDate < startOfDay) return false;
        }
        
        if (filters.endDate) {
          const endOfDay = new Date(filters.endDate);
          endOfDay.setHours(23, 59, 59, 999);
          if (docDate > endOfDay) return false;
        }
      }

      return true;
    });
  }, [documents, filters]);

  const handleDownload = (doc: Document) => {
    toast.success(`Downloading ${doc.name}...`);
    // Simulate download
    console.log("Downloading:", doc);
  };

  const handleEditWorkflow = (doc: Document) => {
    setSelectedDocument(doc);
    setWorkflowEditorOpen(true);
  };

  const handleSaveWorkflow = (
    documentId: string,
    workflow: string,
    notes: string
  ) => {
    setDocuments((docs) =>
      docs.map((doc) =>
        doc.id === documentId ? { ...doc, workflow } : doc
      )
    );
    toast.success("Workflow updated successfully!");
    console.log("Workflow notes:", notes);
  };

  const handleFilesUploaded = (files: File[]) => {
    toast.success(`${files.length} file(s) uploaded successfully!`);
    // In a real app, you would process and add these to the documents list
    console.log("Uploaded files:", files);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className={`flex h-screen ${darkMode ? "bg-gray-900 text-white" : "bg-white"}`}>
        <SearchFilters
          filters={filters}
          onFiltersChange={setFilters}
          availableTags={availableTags}
          availableAuthors={availableAuthors}
          darkMode={darkMode}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className={`border-b p-6 ${darkMode ? "border-gray-700" : ""}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-blue-600" />
                <div>
                  <h1 className="text-2xl">Document Management System</h1>
                  <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                    {filteredDocuments.length} document(s) found
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex gap-2">
                  <Button
                    variant={viewMode === "compact" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("compact")}
                    title="Compact View"
                  >
                    <AlignJustify className="w-4 h-4" />
                  </Button>
                  <Button
                    variant={viewMode === "grid" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("grid")}
                    title="Grid View"
                  >
                    <Grid3x3 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant={viewMode === "list" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("list")}
                    title="List View"
                  >
                    <List className="w-4 h-4" />
                  </Button>
                  <Button
                    variant={viewMode === "grouped" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setViewMode("grouped")}
                    title="Grouped by Type"
                  >
                    <Layers className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDarkMode(!darkMode)}
                    title="Toggle Dark Mode"
                  >
                    {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                  </Button>
                </div>
                <div className={`w-px h-6 ${darkMode ? "bg-gray-700" : "bg-gray-300"}`}></div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => toast.info("Sign in / Profile functionality will be implemented with role-based access")}
                  title="Sign In / Profile"
                  className="gap-2"
                >
                  <UserCircle className="w-4 h-4" />
                  <span className="hidden sm:inline">Profile</span>
                </Button>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-auto p-6">
            <Tabs defaultValue="documents" className="w-full">
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
                {filteredDocuments.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                    <p className="text-gray-500">
                      No documents found matching your filters
                    </p>
                  </div>
                ) : viewMode === "compact" ? (
                  <CompactProjectView
                    documents={filteredDocuments}
                    onDownload={handleDownload}
                    onEditWorkflow={handleEditWorkflow}
                    darkMode={darkMode}
                  />
                ) : viewMode === "grouped" ? (
                  <GroupedDocuments
                    documents={filteredDocuments}
                    onDownload={handleDownload}
                    onEditWorkflow={handleEditWorkflow}
                  />
                ) : (
                  <div
                    className={
                      viewMode === "grid"
                        ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
                        : "space-y-2"
                    }
                  >
                    {filteredDocuments.map((doc) => (
                      <DocumentCard
                        key={doc.id}
                        document={doc}
                        onDownload={handleDownload}
                        onEditWorkflow={handleEditWorkflow}
                      />
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="upload" className="mt-6">
                <div className="max-w-2xl mx-auto">
                  <UploadZone onFilesUploaded={handleFilesUploaded} />
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>

        <WorkflowEditor
          document={selectedDocument}
          open={workflowEditorOpen}
          onOpenChange={setWorkflowEditorOpen}
          onSave={handleSaveWorkflow}
        />

        <Toaster />
      </div>
    </DndProvider>
  );
}