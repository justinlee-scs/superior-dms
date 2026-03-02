import { useState, useMemo } from "react";
import {
  Download,
  FileText,
  Image,
  FileSpreadsheet,
  File,
  Archive,
  ChevronDown,
  ChevronRight,
  ArrowUpDown,
} from "lucide-react";

import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";

import type { Document } from "@/app/components/document-card";
import { SelectionCheckbox } from "@/app/components/selection-checkbox";
import { useSelection } from "@/app/selection/selection-context";

interface CompactProjectViewProps {
  documents: Document[];
  onPreview: (doc: Document) => void;
  onDownload: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onEditWorkflow: (doc: Document) => void;
  onOpenVersions?: (doc: Document) => void;
  darkMode?: boolean;
}

const getFileIcon = (type: string) => {
  if (type.includes("image")) return Image;
  if (type.includes("pdf") || type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel"))
    return FileSpreadsheet;
  if (type.includes("archive")) return Archive;
  return File;
};

const getWorkflowColor = (workflow: string, darkMode?: boolean) => {
  const base =
    "border text-xs font-medium rounded-md px-2 py-0.5 whitespace-nowrap";

  switch (workflow.toLowerCase()) {
    case "approved":
    case "published":
      return `${base} ${darkMode
        ? "bg-green-900/30 text-green-300 border-green-800"
        : "bg-green-100 text-green-800 border-green-200"
        }`;
    case "in review":
    case "pending approval":
      return `${base} ${darkMode
        ? "bg-yellow-900/30 text-yellow-300 border-yellow-800"
        : "bg-yellow-100 text-yellow-800 border-yellow-200"
        }`;
    case "draft":
      return `${base} ${darkMode
        ? "bg-gray-800 text-gray-300 border-gray-700"
        : "bg-gray-100 text-gray-800 border-gray-200"
        }`;
    default:
      return `${base} ${darkMode
        ? "bg-blue-900/30 text-blue-300 border-blue-800"
        : "bg-blue-100 text-blue-800 border-blue-200"
        }`;
  }
};

type SortOption = "date" | "name" | "size";

export function CompactProjectView({
  documents,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  onOpenVersions,
  darkMode,
}: CompactProjectViewProps) {
  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(
    new Set()
  );
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<Record<string, SortOption>>({});

  const selection = useSelection();

  const groupedDocuments = useMemo(() => {
    const projects: Record<string, Record<string, Document[]>> = {};
    documents.forEach((doc) => {
      if (!projects[doc.project]) projects[doc.project] = {};
      const docType = doc.documentType || "Other";
      if (!projects[doc.project][docType]) {
        projects[doc.project][docType] = [];
      }
      projects[doc.project][docType].push(doc);
    });
    return projects;
  }, [documents]);

  const getSortedDocuments = (project: string, docs: Document[]) => {
    const sortOption = sortBy[project] || "date";
    return [...docs].sort((a, b) => {
      switch (sortOption) {
        case "date":
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case "name":
          return a.name.localeCompare(b.name);
        case "size":
          return parseFloat(b.size) - parseFloat(a.size);
        default:
          return 0;
      }
    });
  };

  const selectionState = (docs: Document[]) => {
    const selectedCount = docs.filter((d) =>
      selection.isSelected(d.id)
    ).length;
    return {
      checked: docs.length > 0 && selectedCount === docs.length,
      indeterminate: selectedCount > 0 && selectedCount < docs.length,
    };
  };

  const toggleMany = (docs: Document[]) => {
    const allSelected = docs.every((d) => selection.isSelected(d.id));
    docs.forEach((doc) =>
      allSelected ? selection.remove(doc) : selection.add(doc)
    );
  };

  return (
    <div className="space-y-4">
      {Object.entries(groupedDocuments).map(([project, types]) => {
        const projectDocs = Object.values(types).flat();
        const projectSel = selectionState(projectDocs);
        const isProjectCollapsed = collapsedProjects.has(project);
        const currentSort = sortBy[project] || "date";

        return (
          <div
            key={project}
            className={`border rounded-lg overflow-hidden ${darkMode
              ? "border-gray-800 bg-gray-900"
              : "border-gray-200 bg-white"
              }`}
          >
            {/* Project header */}
            <div
              className={`px-4 py-3 flex justify-between border-b ${darkMode
                ? "bg-gray-800 border-gray-700"
                : "bg-gray-50 border-gray-200"
                }`}
            >
              <div className="flex items-center gap-3">
                <SelectionCheckbox
                  checked={projectSel.checked}
                  indeterminate={projectSel.indeterminate}
                  onToggle={() => toggleMany(projectDocs)}
                />

                <button
                  onClick={() =>
                    setCollapsedProjects((prev) => {
                      const next = new Set(prev);
                      next.has(project)
                        ? next.delete(project)
                        : next.add(project);
                      return next;
                    })
                  }
                  className="flex items-center gap-2"
                >
                  {isProjectCollapsed ? <ChevronRight /> : <ChevronDown />}
                  <span className="font-semibold">{project}</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    ({projectDocs.length} files)
                  </span>
                </button>
              </div>

              {!isProjectCollapsed && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <ArrowUpDown className="w-3 h-3 mr-1" />
                      Sort
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() =>
                        setSortBy({ ...sortBy, [project]: "date" })
                      }
                    >
                      Date {currentSort === "date" && "✓"}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortBy({ ...sortBy, [project]: "name" })
                      }
                    >
                      Name {currentSort === "name" && "✓"}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        setSortBy({ ...sortBy, [project]: "size" })
                      }
                    >
                      Size {currentSort === "size" && "✓"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>

            {!isProjectCollapsed &&
              Object.entries(types).map(([docType, docs]) => {
                const typeKey = `${project}-${docType}`;
                const isTypeCollapsed = collapsedTypes.has(typeKey);
                const sortedDocs = getSortedDocuments(project, docs);
                const typeSel = selectionState(sortedDocs);

                return (
                  <div key={typeKey}>
                    {/* Type header */}
                    <div
                      className={`flex items-center gap-3 px-8 py-2 text-sm ${darkMode
                        ? "bg-gray-800 border-gray-700"
                        : "bg-gray-50 border-gray-200"
                        }`}
                    >
                      <SelectionCheckbox
                        checked={typeSel.checked}
                        indeterminate={typeSel.indeterminate}
                        onToggle={() => toggleMany(sortedDocs)}
                      />

                      <button
                        onClick={() =>
                          setCollapsedTypes((prev) => {
                            const next = new Set(prev);
                            next.has(typeKey)
                              ? next.delete(typeKey)
                              : next.add(typeKey);
                            return next;
                          })
                        }
                        className="flex items-center gap-2"
                      >
                        {isTypeCollapsed ? (
                          <ChevronRight />
                        ) : (
                          <ChevronDown />
                        )}
                        <span className="font-medium">{docType}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          ({sortedDocs.length})
                        </span>
                      </button>
                    </div>

                    {!isTypeCollapsed &&
                      sortedDocs.map((doc) => {
                        const FileIcon = getFileIcon(doc.type);
                        const checked = selection.isSelected(doc.id);

                        return (
                          <div
                            key={doc.id}
                            className={`flex items-center gap-3 pl-20 pr-4 py-2 border-t group transition-colors ${darkMode
                              ? "border-gray-800 hover:bg-gray-800/60"
                              : "border-gray-200 hover:bg-blue-50"
                              }`}
                          >
                            <SelectionCheckbox
                              checked={checked}
                              onToggle={() => selection.toggle(doc)}
                            />

                            <FileIcon className="w-4 h-4 text-gray-500" />

                            <div className="flex-1 min-w-0">
                              <span className="text-sm truncate block">
                                {doc.name}
                              </span>
                              <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                                <span className="rounded bg-gray-100 px-1.5 py-0.5">
                                  v{doc.currentVersionNumber ?? 1}
                                </span>
                                <button
                                  type="button"
                                  className="text-blue-600 hover:underline"
                                  onClick={() => onOpenVersions?.(doc)}
                                >
                                  {doc.versionCount ?? 1} ver.
                                </button>
                              </div>
                            </div>

                            <div className="w-28 text-xs text-gray-500">
                              {new Date(doc.date).toLocaleDateString()}
                            </div>

                            <div className="w-36 text-xs text-gray-600 dark:text-gray-400 truncate">
                              {doc.author}
                            </div>

                            <div className="w-32">
                              <span
                                className={getWorkflowColor(
                                  doc.workflow,
                                  darkMode
                                )}
                              >
                                {doc.workflow}
                              </span>
                            </div>

                            <div className="w-20 text-xs text-right text-gray-500">
                              {doc.size}
                            </div>

                            <div className="opacity-0 group-hover:opacity-100">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    ⋯
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={() => onPreview(doc)}
                                  >
                                    Preview
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => onDownload(doc)}
                                  >
                                    <Download className="w-4 h-4 mr-2" />
                                    Download
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => onDelete(doc)}
                                  >
                                    Delete
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => onEditWorkflow(doc)}
                                  >
                                    Edit Workflow
                                  </DropdownMenuItem>
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
        );
      })}
    </div>
  );
}
