import { Button } from "@/app/components/ui/button";
import type { Document } from "@/app/components/document-card";

export function BulkActionBar({
  count,
  onDownload,
  onDelete,
  onClear,
}: {
  count: number;
  onDownload: () => void;
  onDelete: () => void;
  onClear: () => void;
}) {
  if (count === 0) return null;

  return (
    <div className="sticky top-0 z-40 bg-white border-b p-4 flex items-center gap-3">
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
