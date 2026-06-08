import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog";
import { Input } from "@/app/components/ui/input";

import type { Document } from "@/app/components/document-card";

interface TagEditorDialogProps {
  open: boolean;
  document: Document | null;
  availableTags: string[];
  onOpenChange: (open: boolean) => void;
  onSave: (payload: { tags: string[]; dueDate: string | null }) => Promise<void> | void;
  darkMode?: boolean;
}

export function TagEditorDialog({
  open,
  document,
  availableTags,
  onOpenChange,
  onSave,
  darkMode,
}: TagEditorDialogProps) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [searchTag, setSearchTag] = useState("");
  const [dueDate, setDueDate] = useState<string>("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelectedTags(document?.tags ?? []);
    setNewTag("");
    setSearchTag("");
    setDueDate(document?.dueDate ?? "");
  }, [open, document]);

  const visiblePool = useMemo(() => {
    if (!searchTag.trim()) return availableTags;
    const q = searchTag.trim().toLowerCase();
    return availableTags.filter((tag) => tag.toLowerCase().includes(q));
  }, [availableTags, searchTag]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag],
    );
  };

  const addNewTag = () => {
    const normalized = newTag.trim().toLowerCase().replace(/\s+/g, "_");
    if (!normalized) return;
    setSelectedTags((prev) => (prev.includes(normalized) ? prev : [...prev, normalized]));
    setNewTag("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={`sm:max-w-2xl ${darkMode ? "bg-gray-900 text-white border-gray-700" : ""}`}>
        <DialogHeader>
          <DialogTitle className={darkMode ? "text-white" : ""}>Document Details</DialogTitle>
          <DialogDescription className={darkMode ? "text-gray-400" : ""}>
            {document ? `Update tags and due date for ${document.name}` : "Update details"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Due date</p>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className={darkMode ? "bg-gray-800 border-gray-700 text-white" : ""}
            />
          </div>

          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Find tags</p>
            <Input
              value={searchTag}
              onChange={(e) => setSearchTag(e.target.value)}
              placeholder="Search existing tags..."
              className={darkMode ? "bg-gray-800 border-gray-700 text-white placeholder:text-gray-500" : ""}
            />
          </div>

          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Existing pool</p>
            <div className={`max-h-44 overflow-auto rounded-md border p-2 ${darkMode ? "border-gray-700 bg-gray-800" : ""}`}>
              <div className="flex flex-wrap gap-2">
                {visiblePool.map((tag) => {
                  const selected = selectedTags.includes(tag);
                  return (
                    <Badge
                      key={tag}
                      variant={selected ? "default" : "outline"}
                      className={`cursor-pointer ${!selected && darkMode ? "border-gray-500 text-gray-300" : ""}`}
                      onClick={() => toggleTag(tag)}
                    >
                      {tag}
                    </Badge>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Create and add a new tag</p>
            <div className="flex gap-2">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="e.g. project:apollo"
                className={darkMode ? "bg-gray-800 border-gray-700 text-white placeholder:text-gray-500" : ""}
              />
              <Button type="button" variant="outline" onClick={addNewTag} disabled={!newTag.trim()}
                className={darkMode ? "border-gray-600 text-gray-300 hover:bg-gray-700" : ""}
              >
                Add
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Selected for this document</p>
            <div className={`rounded-md border p-2 min-h-12 ${darkMode ? "border-gray-700 bg-gray-800" : ""}`}>
              <div className="flex flex-wrap gap-2">
                {selectedTags.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}
            className={darkMode ? "text-gray-300 hover:bg-gray-700" : ""}
          >
            Cancel
          </Button>
          <Button
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave({ tags: selectedTags, dueDate: dueDate || null });
              } finally {
                setSaving(false);
                onOpenChange(false);
              }
            }}
          >
            {saving ? "Saving..." : "Save Details"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}