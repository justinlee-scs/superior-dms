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
  onReprocess?: (doc: Document) => void;
  darkMode?: boolean;
}

const getDocumentTypeLabel = (type: string) => {
  if (type.includes("pdf")) return "PDF Documents";
  if (type.includes("document")) return "Documents";
  if (type.includes("spreadsheet") || type.includes("excel")) return "Spreadsheets";
  if (type.includes("image")) return "Images";
  return "Other Files";
};

const getDocumentTypeIcon = (type: string) => {
  if (type.includes("pdf")) return FileText;
  if (type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel")) return FileSpreadsheet;
  if (type.includes("image")) return Image;
  return File;
};

const getTypeCategory = (type: string) => {
  if (type.includes("pdf")) return "pdf";
  if (type.includes("document")) return "document";
  if (type.includes("spreadsheet") || type.includes("excel")) return "spreadsheet";
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
  onReprocess,
  darkMode,
}: GroupedDocumentsProps) {
  // Group documents by type
  const groupedByType = documents.reduce((acc, doc) => {
    const category = getTypeCategory(doc.type);
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(doc);
    return acc;
  }, {} as Record<string, Document[]>);

  // Get projects represented in the documents
  const projects = Array.from(new Set(documents.map((doc) => doc.project)));

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className={`w-16 h-16 mx-auto mb-4 ${darkMode ? "text-gray-500" : "text-gray-300"}`} />
        <p className={darkMode ? "text-gray-400" : "text-gray-500"}>No documents found</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Project Summary */}
      {projects.length > 0 && (
        <div className={`rounded-lg border p-4 ${darkMode ? "border-gray-700 bg-gray-800" : "border-blue-200 bg-blue-50"}`}>
          <h3 className={`mb-2 font-medium ${darkMode ? "text-gray-100" : ""}`}>
            {projects.length === 1 ? "Project" : "Projects"} Found
          </h3>
          <div className="flex flex-wrap gap-2">
            {projects.map((project) => {
              const count = documents.filter((doc) => doc.project === project).length;
              return (
                <Badge
                  key={project}
                  variant="secondary"
                  className={`text-sm ${darkMode ? "bg-gray-700 text-gray-100" : ""}`}
                >
                  {project} ({count} {count === 1 ? "file" : "files"})
                </Badge>
              );
            })}
          </div>
        </div>
      )}

      {/* Grouped Documents */}
      {Object.entries(groupedByType).map(([typeKey, docs]) => {
        const TypeIcon = getDocumentTypeIcon(typeKey);
        const typeLabel = getDocumentTypeLabel(typeKey);

        return (
          <div key={typeKey} className="space-y-4">
            <div className={`flex items-center gap-3 border-b pb-2 ${darkMode ? "border-gray-700" : ""}`}>
              <TypeIcon className={`w-5 h-5 ${darkMode ? "text-gray-300" : "text-gray-600"}`} />
              <h2 className={`text-lg font-semibold ${darkMode ? "text-gray-100" : ""}`}>{typeLabel}</h2>
              <Badge variant="outline" className={darkMode ? "border-gray-600 text-gray-200" : ""}>{docs.length}</Badge>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {docs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onPreview={() => onPreview(doc)}
                  onDownload={() => onDownload(doc)}
                  onDelete={async () => onDelete(doc)}
                  onEditWorkflow={() => onEditWorkflow(doc)}
                  onEditTags={() => onEditTags?.(doc)}
                  onReprocess={() => onReprocess?.(doc)}
                  darkMode={darkMode}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
