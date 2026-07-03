import { useState } from "react";
import {
  CheckCircle2,
  Download,
  FileText,
  Image,
  FileSpreadsheet,
  File,
  Archive,
  Clock3,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";
import { formatBytes, formatLocalDateFromDateOnly, formatPageCount } from "@/lib/format";
import { normalizeWorkflowStatus } from "@/lib/dms";
import { MoveProjectDialog } from "@/app/components/move-project-dialog";
import { RenameDocumentDialog } from "@/app/components/rename-document-dialog";

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
  inWorkspace?: boolean;
  workflowNotes?: string | null;
}

interface DocumentCardProps {
  document: Document;
  onPreview?: (doc: Document) => void;
  onDownload?: (doc: Document) => void;
  onDelete?: (doc: Document) => void;
  onEditWorkflow?: (doc: Document) => void;
  onEditTags?: (doc: Document) => void;
  onMoveProject?: (doc: Document, projectName: string) => Promise<void>;
  onReprocess?: (doc: Document) => void;
  availableTags?: string[];
  darkMode?: boolean;
  onRename?: (doc: Document, newName: string) => Promise<void>;
}

const getFileIcon = (type: string) => {
  if (type.includes("image")) return Image;
  if (type.includes("pdf") || type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel")) return FileSpreadsheet;
  if (type.includes("archive")) return Archive;
  return File;
};

const getWorkflowColor = (workflow: string) => {
  switch (normalizeWorkflowStatus(workflow).toLowerCase()) {
    case "processing":
      return "bg-amber-100 text-amber-800 border-amber-300";
    case "failed":
      return "bg-red-100 text-red-800 border-red-300";
    case "uploaded":
      return "bg-green-100 text-green-800 border-green-300";
    case "approved":
    case "published":
      return "bg-green-100 text-green-800 border-green-200";
    case "in review":
    case "needs review":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "draft":
      return "bg-gray-100 text-gray-800 border-gray-200";
    default:
      return "bg-blue-100 text-blue-800 border-blue-200";
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

export function DocumentCard({
  document,
  onPreview,
  onDownload,
  onDelete,
  onEditWorkflow,
  onEditTags,
  onMoveProject,
  onRename,
  onReprocess,
  availableTags = [],
  darkMode,
}: DocumentCardProps) {
  const FileIcon = getFileIcon(document.type);
  const [moveProjectOpen, setMoveProjectOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);

  return (
    <>
      <div
        className={`flex items-center gap-3 p-4 border rounded-lg transition-colors ${darkMode ? "bg-gray-800 border-gray-700 hover:bg-gray-750" : "bg-white border-gray-200 hover:bg-blue-50"
          }`}
      >
        {/* File Icon */}
        <FileIcon className={`w-5 h-5 flex-shrink-0 ${darkMode ? "text-gray-400" : "text-gray-500"}`} />

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className={`font-medium truncate ${darkMode ? "text-gray-200" : ""}`}>{document.name}</div>
          <div className={`text-xs truncate ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
            {document.author} • {formatLocalDateFromDateOnly(document.date)} • {formatPageCount(document.pageCount)} • {formatBytes(document.sizeBytes)}
          </div>
        </div>

        {/* Workflow Badge */}
        <div className="flex-shrink-0">
          <Badge
            variant="outline"
            className={`text-xs inline-flex items-center gap-1 ${getWorkflowColor(document.workflow)}`}
          >
            {getWorkflowIcon(document.workflow)}
            {normalizeWorkflowStatus(document.workflow)}
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
              {onDownload && <DropdownMenuItem onClick={() => onDownload(document)}>Download</DropdownMenuItem>}
              {onDelete && <DropdownMenuItem onClick={() => onDelete(document)}>Delete</DropdownMenuItem>}
              {onEditWorkflow && <DropdownMenuItem onClick={() => onEditWorkflow(document)}>Edit Workflow</DropdownMenuItem>}
              {onEditTags && <DropdownMenuItem onClick={() => onEditTags(document)}>Edit Tags</DropdownMenuItem>}
              {onMoveProject && (
                <DropdownMenuItem onClick={() => setMoveProjectOpen(true)}>
                  Move Project
                </DropdownMenuItem>
              )}
              {onRename && (
                <DropdownMenuItem onClick={() => setRenameOpen(true)}>Rename</DropdownMenuItem>
              )}
              {onReprocess && <DropdownMenuItem onClick={() => onReprocess(document)}>Reprocess</DropdownMenuItem>}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {onRename && (
        <RenameDocumentDialog
          open={renameOpen}
          onOpenChange={setRenameOpen}
          currentName={document.name}
          darkMode={darkMode}
          onApply={async (newName) => {
            await onRename(document, newName);
          }}
        />
      )}
      {onMoveProject && (
        <MoveProjectDialog
          open={moveProjectOpen}
          onOpenChange={setMoveProjectOpen}
          availableTags={availableTags}
          darkMode={darkMode}
          onApply={async (projectName) => {
            await onMoveProject(document, projectName);
            setMoveProjectOpen(false);
          }}
        />
      )}
    </>
  );
}