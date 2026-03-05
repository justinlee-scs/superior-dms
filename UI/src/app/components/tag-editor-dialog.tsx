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
  onSave: (tags: string[]) => Promise<void> | void;
}

export function TagEditorDialog({
  open,
  document,
  availableTags,
  onOpenChange,
  onSave,
}: TagEditorDialogProps) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [searchTag, setSearchTag] = useState("");

  useEffect(() => {
    if (!open) return;
    setSelectedTags(document?.tags ?? []);
    setNewTag("");
    setSearchTag("");
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
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit Tags</DialogTitle>
          <DialogDescription>
            {document ? `Set tags for ${document.name}` : "Set tags"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">Find tags</p>
            <Input
              value={searchTag}
              onChange={(e) => setSearchTag(e.target.value)}
              placeholder="Search existing tags..."
            />
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">Existing pool</p>
            <div className="max-h-44 overflow-auto rounded-md border p-2">
              <div className="flex flex-wrap gap-2">
                {visiblePool.map((tag) => {
                  const selected = selectedTags.includes(tag);
                  return (
                    <Badge
                      key={tag}
                      variant={selected ? "default" : "outline"}
                      className="cursor-pointer"
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
            <p className="text-sm font-medium">Create and add a new tag</p>
            <div className="flex gap-2">
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="e.g. project:apollo"
              />
              <Button type="button" variant="outline" onClick={addNewTag} disabled={!newTag.trim()}>
                Add
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">Selected for this document</p>
            <div className="rounded-md border p-2 min-h-12">
              <div className="flex flex-wrap gap-2">
                {selectedTags.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={async () => {
              await onSave(selectedTags);
              onOpenChange(false);
            }}
          >
            Save Tags
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
