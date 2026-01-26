import { useState, useMemo } from "react";
import { Download, FileText, Image, FileSpreadsheet, File, Archive, ChevronDown, ChevronRight, ArrowUpDown } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import type { Document } from "@/app/components/document-card";

interface CompactProjectViewProps {
  documents: Document[];
  onPreview: (doc: Document) => void;
  onDownload: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onEditWorkflow: (doc: Document) => void;
  darkMode?: boolean;
}

const getFileIcon = (type: string) => {
  if (type.includes("image")) return Image;
  if (type.includes("pdf") || type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel")) return FileSpreadsheet;
  if (type.includes("archive")) return Archive;
  return File;
};

const getWorkflowColor = (workflow: string) => {
  switch (workflow.toLowerCase()) {
    case "approved":
    case "published":
      return "bg-green-100 text-green-800 border-green-200";
    case "in review":
    case "pending approval":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "draft":
      return "bg-gray-100 text-gray-800 border-gray-200";
    default:
      return "bg-blue-100 text-blue-800 border-blue-200";
  }
};

type SortOption = "date" | "name" | "size";

export function CompactProjectView({
  documents,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  darkMode,
}: CompactProjectViewProps) {
  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(new Set());
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<Record<string, SortOption>>({});

  const groupedDocuments = useMemo(() => {
    const projects: Record<string, Record<string, Document[]>> = {};
    documents.forEach((doc) => {
      if (!projects[doc.project]) projects[doc.project] = {};
      const docType = doc.documentType || "Other";
      if (!projects[doc.project][docType]) projects[doc.project][docType] = [];
      projects[doc.project][docType].push(doc);
    });
    return projects;
  }, [documents]);

  const toggleProject = (project: string) => {
    setCollapsedProjects((prev) => {
      const next = new Set(prev);
      next.has(project) ? next.delete(project) : next.add(project);
      return next;
    });
  };

  const toggleType = (key: string) => {
    setCollapsedTypes((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const getSortedDocuments = (project: string, docs: Document[]): Document[] => {
    const sortOption = sortBy[project] || "date";
    return [...docs].sort((a, b) => {
      switch (sortOption) {
        case "date":
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case "name":
          return a.name.localeCompare(b.name);
        case "size":
          const sizeA = parseFloat(a.size);
          const sizeB = parseFloat(b.size);
          return sizeB - sizeA;
        default:
          return 0;
      }
    });
  };

  const changeSortOption = (project: string, option: SortOption) => {
    setSortBy((prev) => ({ ...prev, [project]: option }));
  };

  return (
    <div className="space-y-4">
      {Object.entries(groupedDocuments).map(([project, types]) => {
        const isProjectCollapsed = collapsedProjects.has(project);
        const projectDocs = Object.values(types).flat();
        const currentSort = sortBy[project] || "date";
        const projectNumber = projectDocs[0]?.projectNumber;

        return (
          <div key={project} className={`border rounded-lg overflow-hidden ${darkMode ? "bg-gray-800 border-gray-700" : "bg-white"}`}>
            {/* Project Header */}
            <div className={`border-b px-4 py-3 ${darkMode ? "bg-gray-900 border-gray-700" : "bg-gray-50"}`}>
              <div className="flex items-center justify-between">
                <button
                  onClick={() => toggleProject(project)}
                  className={`flex items-center gap-2 transition-colors ${darkMode ? "hover:text-blue-400" : "hover:text-blue-600"}`}
                >
                  {isProjectCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  <span className="font-semibold text-base">{project}</span>
                  {projectNumber && (
                    <span className={`text-xs px-2 py-0.5 rounded ${darkMode ? "bg-gray-700 text-gray-300" : "bg-gray-200 text-gray-600"}`}>
                      {projectNumber}
                    </span>
                  )}
                  <span className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                    ({projectDocs.length} {projectDocs.length === 1 ? "file" : "files"})
                  </span>
                </button>

                {!isProjectCollapsed && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-8 gap-2">
                        <ArrowUpDown className="w-3 h-3" />
                        Sort: {currentSort === "date" ? "Date" : currentSort === "name" ? "Name" : "Size"}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => changeSortOption(project, "date")}>
                        Sort by Date {currentSort === "date" && "✓"}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => changeSortOption(project, "name")}>
                        Sort by Name {currentSort === "name" && "✓"}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => changeSortOption(project, "size")}>
                        Sort by Size {currentSort === "size" && "✓"}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </div>

            {/* Document Types */}
            {!isProjectCollapsed && (
              <div>
                {Object.entries(types).map(([docType, docs]) => {
                  const typeKey = `${project}-${docType}`;
                  const isTypeCollapsed = collapsedTypes.has(typeKey);
                  const sortedDocs = getSortedDocuments(project, docs);

                  return (
                    <div key={typeKey} className={`border-b last:border-b-0 ${darkMode ? "border-gray-700" : ""}`}>
                      {/* Document Type Header */}
                      <button
                        onClick={() => toggleType(typeKey)}
                        className={`w-full px-8 py-2 flex items-center gap-2 transition-colors text-sm ${
                          darkMode ? "bg-gray-850 hover:bg-gray-800" : "bg-gray-25 hover:bg-gray-100"
                        }`}
                      >
                        {isTypeCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        <span className={`font-medium ${darkMode ? "text-gray-300" : "text-gray-700"}`}>{docType}</span>
                        <span className={`text-xs ${darkMode ? "text-gray-500" : "text-gray-500"}`}>({docs.length})</span>
                      </button>

                      {/* Document List */}
                      {!isTypeCollapsed &&
                        sortedDocs.map((doc) => {
                          const FileIcon = getFileIcon(doc.type);
                          return (
                            <div
                              key={doc.id}
                              className={`flex items-center gap-3 pl-20 pr-4 py-2 transition-colors border-t first:border-t-0 group ${
                                darkMode ? "hover:bg-gray-750 border-gray-700" : "hover:bg-blue-50"
                              }`}
                            >
                              <FileIcon className={`w-4 h-4 flex-shrink-0 ${darkMode ? "text-gray-400" : "text-gray-500"}`} />
                              <div className="flex-1 min-w-0">
                                <span className={`text-sm truncate block ${darkMode ? "text-gray-200" : ""}`}>{doc.name}</span>
                              </div>
                              <div className={`w-28 flex-shrink-0 text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                {new Date(doc.date).toLocaleDateString()}
                              </div>
                              <div className={`w-36 flex-shrink-0 text-xs truncate ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                                {doc.author}
                              </div>
                              <div className="w-32 flex-shrink-0">
                                <Badge variant="outline" className={`text-xs ${getWorkflowColor(doc.workflow)}`}>
                                  {doc.workflow}
                                </Badge>
                              </div>
                              <div className={`w-20 flex-shrink-0 text-xs text-right ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                {doc.size}
                              </div>

                              {/* Actions Dropdown */}
                              <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                                      <span className="sr-only">Open menu</span>
                                      <span className="text-xs">⋯</span>
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    <DropdownMenuItem onClick={() => onPreview(doc)}>Preview</DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => onDownload(doc)}>
                                      <Download className="w-4 h-4 mr-2" />
                                      Download
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => onDelete(doc)}>Delete</DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => onEditWorkflow(doc)}>Edit Workflow</DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
