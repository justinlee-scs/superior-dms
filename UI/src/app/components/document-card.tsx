import { Download, FileText, Image, FileSpreadsheet, File, MoreVertical } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu";

export interface Document {
  id: string;
  name: string;
  type: string;
  size: string;
  author: string;
  date: string;
  tags: string[];
  workflow: string;
  project: string;
  documentType?: string; // Invoice, Contract, Statement, Report, etc.
  vendor?: string; // Vendor/supplier name
  projectNumber?: string; // Project number/ID
}

interface DocumentCardProps {
  document: Document;
  onDownload: (doc: Document) => void;
  onEditWorkflow: (doc: Document) => void;
  onDelete: (doc: Document) => Promise<void>;
}

const getFileIcon = (type: string) => {
  if (type.includes("image")) return Image;
  if (type.includes("pdf") || type.includes("document")) return FileText;
  if (type.includes("spreadsheet") || type.includes("excel")) return FileSpreadsheet;
  return File;
};

export function DocumentCard({ document, onDownload, onEditWorkflow, onDelete }: DocumentCardProps) {
  const FileIcon = getFileIcon(document.type);

  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <FileIcon className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="font-medium text-sm">{document.name}</h3>
            <p className="text-xs text-gray-500">{document.size}</p>
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <MoreVertical className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onDownload(document)}>
              <Download className="w-4 h-4 mr-2" />
              Download
            </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onEditWorkflow(document)}>
                Edit Workflow
            </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDelete(document)}>
                Delete
              </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Project:</span>
          <span className="font-medium">{document.project}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Author:</span>
          <span>{document.author}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Date:</span>
          <span>{document.date}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Workflow:</span>
          <Badge variant="outline" className="text-xs">
            {document.workflow}
          </Badge>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 mt-3">
        {document.tags.map((tag) => (
          <Badge key={tag} variant="secondary" className="text-xs">
            {tag}
          </Badge>
        ))}
      </div>
    </div>
  );
}