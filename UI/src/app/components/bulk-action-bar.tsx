import { Button } from "@/app/components/ui/button";
import type { Document } from "@/app/components/document-card";


interface BulkActionBarProps {
  documents: Document[];
  darkMode?: boolean;
  count: number;
  onDownload: () => void;
  onDelete: () => void;
  onClear: () => void;
}

export function BulkActionBar({
  count,
  onDownload,
  onDelete,
  onClear,
  darkMode,
}: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div className={`flex items-center gap-3 px-8 py-2 text-sm ${darkMode
      ? "border-gray-600 bg-gray-800/60"
      : "border-gray-300 bg-gray-100"
      }`}>
      <span className="text-sm font-medium">{count} selected</span>
      <Button size="sm" onClick={onDownload}>
        Download
      </Button>
      {/* <Button size="sm" variant="destructive" onClick={onDelete}>
        Delete
      </Button> */}
      <Button size="sm" variant="ghost" onClick={onClear}>
        Clear
      </Button>
    </div>
  );
}
