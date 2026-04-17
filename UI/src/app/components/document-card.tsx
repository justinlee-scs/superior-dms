import { Download, FileText, Image, FileSpreadsheet, File, Archive } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import { formatBytes, formatPageCount } from "@/lib/format";

export interface Document {
  id: string;
  name: string;
  type: string;
  size: string;
  sizeBytes?: number | null;
  author: string;
  date: string;
  tags: string[];
  workflow: string;
  project: string;
  documentType?: string;
  vendor?: string;
  projectNumber?: string;
  currentVersionId?: string;
  currentVersionNumber?: number;
  versionCount?: number;
  dueDate?: string | null;
  pageCount?: number | null;
}

interface DocumentCardProps {
  document: Document;
  onPreview?: (doc: Document) => void;
  onDownload?: (doc: Document) => void;
  onDelete?: (doc: Document) => void;
  onEditWorkflow?: (doc: Document) => void;
  onEditTags?: (doc: Document) => void;
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
    case "failed":
      return "bg-red-100 text-red-800 border-red-300";
    case "uploaded":
      return "bg-sky-100 text-sky-800 border-sky-300";
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

export function DocumentCard({
  document,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  onEditTags,
  darkMode,
}: DocumentCardProps) {
  const FileIcon = getFileIcon(document.type);

  return (
    <div
      className={`flex items-center gap-3 p-4 border rounded-lg transition-colors ${
        darkMode ? "bg-gray-800 border-gray-700 hover:bg-gray-750" : "bg-white border-gray-200 hover:bg-blue-50"
      }`}
    >
      {/* File Icon */}
      <FileIcon className={`w-5 h-5 flex-shrink-0 ${darkMode ? "text-gray-400" : "text-gray-500"}`} />

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <div className={`font-medium truncate ${darkMode ? "text-gray-200" : ""}`}>{document.name}</div>
        <div className={`text-xs truncate ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
          {document.author} • {new Date(document.date).toLocaleDateString()} • {formatPageCount(document.pageCount)} • {formatBytes(document.sizeBytes)}
        </div>
      </div>

      {/* Workflow Badge */}
      <div className="flex-shrink-0">
        <Badge variant="outline" className={`text-xs ${getWorkflowColor(document.workflow)}`}>
          {document.workflow}
        </Badge>
      </div>

      {/* Actions Dropdown */}
      <div className="flex-shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
              <span className="sr-only">Open menu</span>
              <span className="text-xs">⋯</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {onPreview && <DropdownMenuItem onClick={() => onPreview(document)}>Preview</DropdownMenuItem>}
            {onDownload && (<DropdownMenuItem onClick={() => onDownload(document)}>Download</DropdownMenuItem>)}
            {onDelete && <DropdownMenuItem onClick={() => onDelete(document)}>Delete</DropdownMenuItem>}
            {onEditWorkflow && <DropdownMenuItem onClick={() => onEditWorkflow(document)}>Edit Workflow</DropdownMenuItem>}
            {onEditTags && <DropdownMenuItem onClick={() => onEditTags(document)}>Edit Tags</DropdownMenuItem>}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
