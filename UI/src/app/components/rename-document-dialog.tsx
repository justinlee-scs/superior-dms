import { useEffect, useState } from "react";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/app/components/ui/dialog";

interface RenameDocumentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentName: string;
  darkMode?: boolean;
  onApply: (newName: string) => Promise<void>;
}

export function RenameDocumentDialog({
  open,
  onOpenChange,
  currentName,
  darkMode,
  onApply,
}: RenameDocumentDialogProps) {
  const [name, setName] = useState(currentName);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset the input whenever the dialog is (re)opened for a given document
  useEffect(() => {
    if (open) {
      setName(currentName);
      setError(null);
    }
  }, [open, currentName]);

  const trimmed = name.trim();
  const isUnchanged = trimmed === currentName.trim();
  const isInvalid = trimmed.length === 0;

  const handleSubmit = async () => {
    if (isInvalid || isUnchanged) return;
    setSaving(true);
    setError(null);
    try {
      await onApply(trimmed);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename document");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100" : ""}>
        <DialogHeader>
          <DialogTitle>Rename Document</DialogTitle>
        </DialogHeader>

        <div className="py-2">
          <Input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            placeholder="Document name"
            className={darkMode ? "bg-gray-900 border-gray-600 text-gray-100" : ""}
          />
          {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isInvalid || isUnchanged || saving}>
            {saving ? "Renaming..." : "Rename"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}