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
  canDeletePoolTags?: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (payload: { tags: string[]; dueDate: string | null }) => Promise<void> | void;
  onDeletePoolTag?: (tag: string) => Promise<void> | void;
}

export function TagEditorDialog({
  open,
  document,
  availableTags,
  canDeletePoolTags,
  onOpenChange,
  onSave,
  onDeletePoolTag,
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
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Document Details</DialogTitle>
          <DialogDescription>
            {document ? `Update tags and due date for ${document.name}` : "Update details"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">Due date</p>
            <Input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

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
            {!canDeletePoolTags && (
              <p className="text-xs text-gray-500">
                You can select tags, but deleting from pool requires tag delete/edit permission.
              </p>
            )}
            <div className="max-h-44 overflow-auto rounded-md border p-2">
              <div className="flex flex-wrap gap-2">
                {visiblePool.map((tag) => {
                  const selected = selectedTags.includes(tag);
                  return (
                    <div key={tag} className="inline-flex items-center gap-1">
                      <Badge
                        variant={selected ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => toggleTag(tag)}
                      >
                        {tag}
                      </Badge>
                      {canDeletePoolTags && onDeletePoolTag && (
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-6 px-2 text-xs text-red-600 hover:text-red-700"
                          onClick={async (e) => {
                            e.stopPropagation();
                            await onDeletePoolTag(tag);
                            setSelectedTags((prev) => prev.filter((item) => item !== tag));
                          }}
                        >
                          x
                        </Button>
                      )}
                    </div>
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
