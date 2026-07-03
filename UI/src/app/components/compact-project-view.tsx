import { useMemo, useState, useCallback, useEffect, useRef, RefObject } from "react";
import {
  CheckCircle2,
  Archive,
  ArrowUpDown,
  Bookmark,
  BookmarkCheck,
  ChevronDown,
  ChevronRight,
  Clock3,
  File,
  FileSpreadsheet,
  FileText,
  Image,
  MoreVertical,
  XCircle,
  AlertTriangle,
} from "lucide-react";

import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/app/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import type { Document } from "@/app/components/document-card";
import { SelectionCheckbox } from "@/app/components/selection-checkbox";
import { useSelection } from "@/app/selection/selection-context";
import { formatBytes, formatLocalDateFromDateOnly, formatPageCount } from "@/lib/format";
import { normalizeWorkflowStatus } from "@/lib/dms";
import { MoveProjectDialog } from "@/app/components/move-project-dialog";
import { RenameDocumentDialog } from "@/app/components/rename-document-dialog";

interface CompactProjectViewProps {
  documents: Document[];
  onPreview: (doc: Document) => void;
  onDownload: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onEditWorkflow: (doc: Document) => void;
  onEditTags?: (doc: Document) => void;
  onMoveProject?: (doc: Document, projectName: string) => Promise<void>;
  onRename?: (doc: Document, newName: string) => Promise<void>;
  onReprocess?: (doc: Document) => void;
  onOpenVersions?: (doc: Document) => void;
  onToggleWorkspace?: (doc: Document) => void;
  availableTags?: string[];
  darkMode?: boolean;
  /** Ref to the BulkActionBar — B key moves focus there */
  barRef?: RefObject<HTMLDivElement | null>;
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
  switch (normalizeWorkflowStatus(workflow).toLowerCase()) {
    case "processing":
      return `${base} ${darkMode ? "bg-amber-900/35 text-amber-300 border-amber-800" : "bg-amber-100 text-amber-800 border-amber-300"}`;
    case "failed":
      return `${base} ${darkMode ? "bg-red-950/50 text-red-300 border-red-700" : "bg-red-100 text-red-800 border-red-300"}`;
    case "uploaded":
      return `${base} ${darkMode ? "bg-green-900/35 text-green-300 border-green-800" : "bg-green-100 text-green-800 border-green-300"}`;
    case "approved":
    case "published":
      return `${base} ${darkMode ? "bg-green-900/30 text-green-300 border-green-800" : "bg-green-100 text-green-800 border-green-200"}`;
    case "in review":
    case "needs review":
      return `${base} ${darkMode ? "bg-yellow-900/30 text-yellow-300 border-yellow-800" : "bg-yellow-100 text-yellow-800 border-yellow-200"}`;
    case "draft":
      return `${base} ${darkMode ? "bg-gray-800 text-gray-300 border-gray-700" : "bg-gray-100 text-gray-800 border-gray-200"}`;
    default:
      return `${base} ${darkMode ? "bg-blue-900/30 text-blue-300 border-blue-800" : "bg-blue-100 text-blue-800 border-blue-200"}`;
  }
};

const getWorkflowIcon = (workflow: string) => {
  switch (normalizeWorkflowStatus(workflow).toLowerCase()) {
    case "processing":
      return <Clock3 className="h-3.5 w-3.5" />;
    case "failed":
      return <XCircle className="h-3.5 w-3.5" />;
    case "needs review":
      return <AlertTriangle className="h-3.5 w-3.5" />;
    case "uploaded":
      return <CheckCircle2 className="h-3.5 w-3.5" />;
    default:
      return null;
  }
};

type SortOption = "date" | "name" | "size";

export function CompactProjectView({
  documents,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  onEditTags,
  onMoveProject,
  onReprocess,
  onOpenVersions,
  onToggleWorkspace,
  onRename,
  availableTags = [],
  darkMode,
  barRef,
}: CompactProjectViewProps) {
  const isInvoiceDocument = (doc: Document) =>
    (doc.documentType ?? "").toLowerCase().includes("invoice");

  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(
    new Set(),
  );
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<Record<string, SortOption>>({});

  // Track which doc has the Move Project dialog open
  const [moveProjectDoc, setMoveProjectDoc] = useState<Document | null>(null);
  const [renameDoc, setRenameDoc] = useState<Document | null>(null);

  const selection = useSelection();

  // Flat ordered list of all currently visible docs — used for keyboard nav
  const visibleDocs = useMemo(() => {
    const result: Document[] = [];
    const projects: Record<string, Record<string, Document[]>> = {};
    documents.forEach((doc) => {
      if (!projects[doc.project]) projects[doc.project] = {};
      const docType = doc.documentType || "Other";
      if (!projects[doc.project][docType]) projects[doc.project][docType] = [];
      projects[doc.project][docType].push(doc);
    });

    Object.entries(projects).forEach(([project, types]) => {
      if (collapsedProjects.has(project)) return;
      Object.entries(types).forEach(([docType, docs]) => {
        const typeKey = `${project}-${docType}`;
        if (collapsedTypes.has(typeKey)) return;
        const sortOption = sortBy[project] || "date";
        const sorted = [...docs].sort((a, b) => {
          switch (sortOption) {
            case "date": return new Date(b.date).getTime() - new Date(a.date).getTime();
            case "name": return a.name.localeCompare(b.name);
            case "size": return (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
            default: return 0;
          }
        });
        result.push(...sorted);
      });
    });
    return result;
  }, [documents, collapsedProjects, collapsedTypes, sortBy]);

  // Ref to track the anchor point for Shift+Arrow range selection
  const anchorIdRef = useRef<string | null>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Only handle arrow/space when not focused on an input/textarea/select
      const tag = (e.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(tag)) return;
      if (!["ArrowUp", "ArrowDown", " ", "b", "B"].includes(e.key) &&
        !(e.key === "a" && (e.ctrlKey || e.metaKey))) return;

      // B — jump focus to the bulk action bar
      if (e.key === "b" || e.key === "B") {
        e.preventDefault();
        const firstBtn = barRef?.current?.querySelector<HTMLElement>(
          "button:not([disabled])"
        );
        firstBtn?.focus();
        return;
      }

      const currentId = selection.focusedId;
      const currentIdx = visibleDocs.findIndex((d) => d.id === currentId);

      // Ctrl/Cmd+A — select all in the focused row's project group,
      // falling back to all visible docs if no row is focused.
      if (e.key === "a" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        const focusedDoc = visibleDocs.find((d) => d.id === selection.focusedId);
        const docsToSelect = focusedDoc
          ? visibleDocs.filter((d) => d.project === focusedDoc.project)
          : visibleDocs;
        docsToSelect.forEach((d) => selection.add(d));
        return;
      }

      // Space — toggle selection on focused row
      if (e.key === " ") {
        e.preventDefault();
        if (currentId) {
          const doc = visibleDocs.find((d) => d.id === currentId);
          if (doc) {
            selection.toggle(doc);
            anchorIdRef.current = currentId;
          }
        }
        return;
      }

      // Arrow keys
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const direction = e.key === "ArrowDown" ? 1 : -1;
        const nextIdx = currentIdx === -1
          ? (direction === 1 ? 0 : visibleDocs.length - 1)
          : Math.max(0, Math.min(visibleDocs.length - 1, currentIdx + direction));
        const nextDoc = visibleDocs[nextIdx];
        if (!nextDoc) return;

        selection.setFocusedId(nextDoc.id);

        if (e.shiftKey) {
          // Shift+Arrow: extend range from anchor to new focused row
          if (!anchorIdRef.current) anchorIdRef.current = currentId ?? nextDoc.id;
          selection.selectRange(visibleDocs, anchorIdRef.current, nextDoc.id);
        } else {
          // Plain arrow: just move focus, update anchor
          anchorIdRef.current = nextDoc.id;
        }

        // Scroll focused row into view
        const el = document.querySelector(`[data-doc-id="${nextDoc.id}"]`);
        el?.scrollIntoView({ block: "nearest" });
      }
    },
    [visibleDocs, selection],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

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

  const getSortedDocuments = (project: string, docs: Document[]) => {
    const sortOption = sortBy[project] || "date";
    return [...docs].sort((a, b) => {
      switch (sortOption) {
        case "date":
          return new Date(b.date).getTime() - new Date(a.date).getTime();
        case "name":
          return a.name.localeCompare(b.name);
        case "size":
          return (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
        default:
          return 0;
      }
    });
  };

  const selectionState = (docs: Document[]) => {
    const selectedCount = docs.filter((d) => selection.isSelected(d.id)).length;
    return {
      checked: docs.length > 0 && selectedCount === docs.length,
      indeterminate: selectedCount > 0 && selectedCount < docs.length,
    };
  };

  const toggleMany = (docs: Document[]) => {
    const allSelected = docs.every((d) => selection.isSelected(d.id));
    docs.forEach((doc) =>
      allSelected ? selection.remove(doc) : selection.add(doc),
    );
  };

  return (
    <>
      <div className="space-y-4">
        {Object.entries(groupedDocuments).map(([project, types]) => {
          const projectDocs = Object.values(types).flat();
          const projectSel = selectionState(projectDocs);
          const isProjectCollapsed = collapsedProjects.has(project);
          const currentSort = sortBy[project] || "date";

          return (
            <div
              key={project}
              className={`overflow-hidden border rounded-xl ${darkMode
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
                        className={`flex items-center gap-3 px-4 py-2 text-sm ${darkMode
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
                          {isTypeCollapsed ? <ChevronRight /> : <ChevronDown />}
                          <span className="font-medium">{docType}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            ({sortedDocs.length})
                          </span>
                        </button>
                      </div>

                      {!isTypeCollapsed && (
                        <div className="overflow-hidden rounded-b-xl">
                          <div className="overflow-x-auto">
                            <Table className="min-w-[1100px] w-full table-fixed">
                              <TableHeader>
                                <TableRow
                                  className={`border-t ${darkMode ? "border-gray-800" : "border-gray-200"
                                    }`}
                                >
                                  {/* checkbox col — matches px-4 of header rows */}
                                  <TableHead className="w-10 pl-4 pr-2" />
                                  <TableHead className="w-[36%] px-2 text-sm">File</TableHead>
                                  <TableHead className="hidden md:table-cell w-[9%] px-2 text-sm">
                                    Versions
                                  </TableHead>
                                  <TableHead className="hidden lg:table-cell w-[11%] px-2 text-sm">
                                    Owner
                                  </TableHead>
                                  <TableHead className="w-[11%] px-2 text-sm">Status</TableHead>
                                  <TableHead className="hidden md:table-cell w-[7%] px-2 text-sm">
                                    Date
                                  </TableHead>
                                  <TableHead className="hidden md:table-cell w-[4%] px-2 text-sm">
                                    Ext.
                                  </TableHead>
                                  <TableHead className="hidden xl:table-cell w-[9%] px-2 text-sm text-right">
                                    Size
                                  </TableHead>
                                  <TableHead className="w-10 px-2 text-sm text-right">
                                    Actions
                                  </TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {sortedDocs.map((doc) => {
                                  const FileIcon = getFileIcon(doc.type);
                                  const checked = selection.isSelected(doc.id);
                                  const isFocused = selection.focusedId === doc.id;

                                  return (
                                    <TableRow
                                      key={doc.id}
                                      data-doc-id={doc.id}
                                      tabIndex={0}
                                      onClick={() => {
                                        selection.setFocusedId(doc.id);
                                        anchorIdRef.current = doc.id;
                                      }}
                                      onFocus={() => selection.setFocusedId(doc.id)}
                                      className={`group transition-colors cursor-pointer outline-none ${isFocused
                                        ? darkMode
                                          ? "border-gray-800 bg-gray-800/60"
                                          : "border-gray-200 bg-blue-50"
                                        : darkMode
                                          ? "border-gray-800 hover:bg-gray-800/60"
                                          : "border-gray-200 hover:bg-blue-50"
                                        }`}
                                    >
                                      {/* Checkbox — pl-4 matches project/type header indent */}
                                      <TableCell className="w-10 pl-4 pr-2 align-middle">
                                        <SelectionCheckbox
                                          checked={checked}
                                          onToggle={() => {
                                            selection.toggle(doc);
                                            selection.setFocusedId(doc.id);
                                            anchorIdRef.current = doc.id;
                                          }}
                                        />
                                      </TableCell>

                                      <TableCell className="px-2 align-middle overflow-hidden">
                                        <span className="block truncate text-sm font-medium">
                                          {doc.name}
                                        </span>
                                      </TableCell>

                                      <TableCell className="hidden md:table-cell px-2 align-middle text-xs text-gray-500">
                                        <div className="flex items-center gap-2">
                                          <span className={`rounded px-1 py-0.5 ${darkMode ? "bg-gray-700 text-gray-300" : "bg-gray-100 text-gray-600"}`}>
                                            v{doc.currentVersionNumber ?? 1}
                                          </span>
                                          <button
                                            type="button"
                                            className="text-blue-600 hover:underline whitespace-nowrap"
                                            onClick={() => onOpenVersions?.(doc)}
                                          >
                                            {doc.versionCount ?? 1} ver.
                                          </button>
                                        </div>
                                      </TableCell>

                                      <TableCell className="hidden lg:table-cell px-2 align-middle text-xs text-gray-600 dark:text-gray-400">
                                        <div className="truncate">{doc.author}</div>
                                      </TableCell>

                                      <TableCell className="px-2 align-middle">
                                        <span
                                          className={`inline-flex items-center gap-1 ${getWorkflowColor(
                                            doc.workflow,
                                            darkMode,
                                          )}`}
                                        >
                                          {getWorkflowIcon(doc.workflow)}
                                          {normalizeWorkflowStatus(doc.workflow)}
                                        </span>
                                      </TableCell>

                                      <TableCell className="hidden md:table-cell px-2 align-middle text-xs text-gray-500">
                                        {formatLocalDateFromDateOnly(doc.date)}
                                      </TableCell>

                                      <TableCell className="hidden md:table-cell px-2 align-middle">
                                        <span className={`rounded px-1 py-0.5 uppercase font-mono text-xs ${darkMode ? "bg-gray-700 text-gray-300" : "bg-gray-100 text-gray-500"}`}>
                                          {doc.type}
                                        </span>
                                      </TableCell>

                                      <TableCell className="hidden xl:table-cell px-2 align-middle text-right text-xs text-gray-500">
                                        <div>{formatPageCount(doc.pageCount)}</div>
                                        <div>{formatBytes(doc.sizeBytes)}</div>
                                      </TableCell>

                                      <TableCell className="w-10 px-2 align-middle text-right">
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
                                            <DropdownMenuItem
                                              onClick={() => onEditTags?.(doc)}
                                            >
                                              Edit Tags
                                            </DropdownMenuItem>
                                            {onMoveProject && (
                                              <DropdownMenuItem
                                                onClick={() => setMoveProjectDoc(doc)}
                                              >
                                                Move Project
                                              </DropdownMenuItem>
                                            )}
                                            {onRename && (
                                              <DropdownMenuItem onClick={() => setRenameDoc(doc)}>
                                                Rename
                                              </DropdownMenuItem>
                                            )}
                                            <DropdownMenuItem
                                              onClick={() => onReprocess?.(doc)}
                                            >
                                              Reprocess
                                            </DropdownMenuItem>
                                          </DropdownMenuContent>
                                        </DropdownMenu>
                                      </TableCell>
                                    </TableRow>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          );
        })}
      </div>

      {/* Move Project dialog — rendered once outside the table to avoid
          nested dialog issues and re-mounting on every row render */}
      {onMoveProject && (
        <MoveProjectDialog
          open={moveProjectDoc !== null}
          onOpenChange={(open) => {
            if (!open) setMoveProjectDoc(null);
          }}
          availableTags={availableTags}
          darkMode={darkMode}
          onApply={async (projectName) => {
            if (moveProjectDoc) {
              await onMoveProject(moveProjectDoc, projectName);
              setMoveProjectDoc(null);
            }
          }}
        />
      )}
      {onRename && (
        <RenameDocumentDialog
          open={renameDoc !== null}
          onOpenChange={(open) => { if (!open) setRenameDoc(null); }}
          currentName={renameDoc ? renameDoc.name : ""}
          darkMode={darkMode}
          onApply={async (newName) => {
            if (renameDoc) {
              await onRename(renameDoc, newName);
              setRenameDoc(null);
            }
          }}
        />
      )}
    </>
  );
}