import { useState } from "react";
import { DocumentCard, type Document } from "@/app/components/document-card";
import { FileText, Image, FileSpreadsheet, File } from "lucide-react";
import { Badge } from "@/app/components/ui/badge";

interface GroupedDocumentsProps {
  documents: Document[];
  onPreview: (doc: Document) => void;
  onDownload: (doc: Document) => void;
  onDelete: (doc: Document) => void;
  onEditWorkflow: (doc: Document) => void;
  onEditTags?: (doc: Document) => void;
  onMoveProject?: (doc: Document) => void;
  onReprocess?: (doc: Document) => void;
  onToggleWorkspace?: (doc: Document) => void;
  darkMode?: boolean;
}

const getDocumentTypeLabel = (type: string) => {
  if (type.includes("pdf")) return "PDF Documents";
  if (type.includes("document")) return "Documents";
  if (type.includes("spreadsheet") || type.includes("excel"))
    return "Spreadsheets";
  if (type.includes("image")) return "Images";
  return "Other Files";
};

const getDocumentTypeIcon = (type: string) => {
  if (type.includes("pdf")) return FileText;
  if (type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel"))
    return FileSpreadsheet;
  if (type.includes("image")) return Image;
  return File;
};

const getTypeCategory = (type: string) => {
  if (type.includes("pdf")) return "pdf";
  if (type.includes("document")) return "document";
  if (type.includes("spreadsheet") || type.includes("excel"))
    return "spreadsheet";
  if (type.includes("image")) return "image";
  return "other";
};

export function GroupedDocuments({
  documents,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  onEditTags,
  onMoveProject,
  onReprocess,
  onToggleWorkspace,
  darkMode,
}: GroupedDocumentsProps) {
  const [collapsedProjects, setCollapsedProjects] = useState<Set<string>>(
    new Set(),
  );
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());

  // Group by project → type
  const grouped = documents.reduce(
    (acc, doc) => {
      if (!acc[doc.project]) acc[doc.project] = {};
      const type = doc.documentType || "Other";
      if (!acc[doc.project][type]) acc[doc.project][type] = [];
      acc[doc.project][type].push(doc);
      return acc;
    },
    {} as Record<string, Record<string, Document[]>>,
  );

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText
          className={`w-16 h-16 mx-auto mb-4 ${
            darkMode ? "text-gray-500" : "text-gray-300"
          }`}
        />
        <p className={darkMode ? "text-gray-400" : "text-gray-500"}>
          No documents found
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([project, types]) => {
        const projectDocs = Object.values(types).flat();
        const isProjectCollapsed = collapsedProjects.has(project);

        return (
          <div
            key={project}
            className={`border rounded-lg overflow-hidden ${
              darkMode
                ? "border-gray-800 bg-gray-900"
                : "border-gray-200 bg-white"
            }`}
          >
            {/* PROJECT HEADER */}
            <div
              className={`px-4 py-3 flex items-center justify-between border-b ${
                darkMode
                  ? "bg-gray-800 border-gray-700"
                  : "bg-gray-50 border-gray-200"
              }`}
            >
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
                <span className="font-semibold">{project}</span>
                <span className="text-sm text-gray-500">
                  ({projectDocs.length} files)
                </span>
              </button>
            </div>

            {!isProjectCollapsed &&
              Object.entries(types).map(([type, docs]) => {
                const typeKey = `${project}-${type}`;
                const isTypeCollapsed = collapsedTypes.has(typeKey);

                const Icon = getDocumentTypeIcon(type);
                const label = getDocumentTypeLabel(type);

                return (
                  <div key={typeKey}>
                    {/* TYPE HEADER */}
                    <div
                      className={`flex items-center gap-2 px-6 py-2 text-sm ${
                        darkMode ? "bg-gray-800" : "bg-gray-50"
                      }`}
                    >
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
                        <Icon className="w-4 h-4" />
                        <span className="font-medium">{label}</span>
                        <span className="text-xs text-gray-500">
                          ({docs.length})
                        </span>
                      </button>
                    </div>

                    {!isTypeCollapsed && (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
                        {docs.map((doc) => (
                          <div
                            key={doc.id}
                            className={`rounded-xl border p-4 transition-colors ${
                              darkMode
                                ? "border-gray-700 bg-gray-800 hover:bg-gray-750"
                                : "border-gray-200 bg-white hover:bg-gray-50"
                            }`}
                          >
                            <div className="min-w-0">
                              <div className="truncate text-sm font-medium">
                                {doc.name}
                              </div>
                              <div className="text-xs text-gray-500">
                                {doc.project}
                              </div>
                            </div>

                            <div className="mt-3 flex flex-wrap gap-2">
                              <button
                                className="text-xs text-blue-600 hover:underline"
                                onClick={() => onPreview(doc)}
                              >
                                Preview
                              </button>
                              <button
                                className="text-xs text-blue-600 hover:underline"
                                onClick={() => onDownload(doc)}
                              >
                                Download
                              </button>
                              <button
                                className="text-xs text-red-600 hover:underline"
                                onClick={() => onDelete(doc)}
                              >
                                Delete
                              </button>
                              <button
                                className="text-xs text-gray-600 hover:underline"
                                onClick={() => onEditWorkflow(doc)}
                              >
                                Workflow
                              </button>
                              <button
                                className="text-xs text-gray-600 hover:underline"
                                onClick={() => onEditTags?.(doc)}
                              >
                                Tags
                              </button>
                              <button
                                className="text-xs text-gray-600 hover:underline"
                                onClick={() => onMoveProject?.(doc)}
                              >
                                Move Project
                              </button>
                              <button
                                className="text-xs text-gray-600 hover:underline"
                                onClick={() => onReprocess?.(doc)}
                              >
                                Reprocess
                              </button>
                            </div>

                            {doc.tags?.length > 0 && (
                              <div className="mt-3 flex flex-wrap gap-1">
                                {doc.tags.slice(0, 4).map((tag) => (
                                  <Badge key={tag} variant="secondary">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        );
      })}
    </div>
  );
}
