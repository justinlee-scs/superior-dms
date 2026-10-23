import { useEffect, useMemo, useState } from "react";
import { createDocumentType, deleteDocumentType, listTagCatalog, type TagCatalogItem } from "@/lib/dms";
import { tagsForDisplay } from "@/lib/tag-display";

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
  onSave: (payload: { tags: string[]; dueDate: string | null; documentTypeTagId: string | null }) => Promise<void> | void;
  darkMode?: boolean;
  canAssignDocumentType?: boolean;
  canCreateDocumentType?: boolean;
  canDeleteDocumentType?: boolean;
}

export function TagEditorDialog({
  open,
  document,
  availableTags,
  onOpenChange,
  onSave,
  darkMode,
  canAssignDocumentType = false,
  canCreateDocumentType = false,
  canDeleteDocumentType = false,
}: TagEditorDialogProps) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [catalog, setCatalog] = useState<TagCatalogItem[]>([]);
  const [documentTypeTagId, setDocumentTypeTagId] = useState("");
  const [newTag, setNewTag] = useState("");
  const [newType, setNewType] = useState("");
  const [typeError, setTypeError] = useState("");
  const [searchTag, setSearchTag] = useState("");
  const [dueDate, setDueDate] = useState<string>("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelectedTags(tagsForDisplay(document?.tags ?? []));
    setDocumentTypeTagId(document?.documentTypeTagId ?? "");
    listTagCatalog().then(setCatalog).catch(() => setCatalog([]));
    setNewTag("");
    setNewType("");
    setTypeError("");
    setSearchTag("");
    setDueDate(document?.dueDate ?? "");
  }, [open, document]);

  const labelTags = useMemo(() => catalog.filter((tag) => tag.kind === "label").map((tag) => tag.name), [catalog]);
  const typeTags = useMemo(() => catalog.filter((tag) => tag.kind === "document_type"), [catalog]);
  const addType = async () => {
    setTypeError("");
    try {
      const created = await createDocumentType(newType.trim());
      setCatalog((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      setDocumentTypeTagId(created.id);
      setNewType("");
    } catch (error) {
      setTypeError(error instanceof Error ? error.message : "Could not add document type");
    }
  };

  const removeType = async (tag: TagCatalogItem) => {
    if (!window.confirm(`Delete document type '${tag.name}'? It must not be assigned to any documents.`)) return;
    setTypeError("");
    try {
      await deleteDocumentType(tag.id);
      setCatalog((current) => current.filter((item) => item.id !== tag.id));
    } catch (error) {
      setTypeError(error instanceof Error ? error.message : "Could not delete document type");
    }
  };

  const visiblePool = useMemo(() => {
    const pool = tagsForDisplay(labelTags.length ? labelTags : availableTags);
    if (!searchTag.trim()) return pool;
    const q = searchTag.trim().toLowerCase();
    return pool.filter((tag) => tag.toLowerCase().includes(q));
  }, [availableTags, labelTags, searchTag]);

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
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Document type</p>
            <select disabled={!canAssignDocumentType} value={documentTypeTagId} onChange={(event) => setDocumentTypeTagId(event.target.value)} className={`h-10 w-full rounded-md border px-3 ${darkMode ? "bg-gray-800 border-gray-700 text-white" : "bg-white"}`}>
              <option value="">No document type</option>
              {typeTags.map((tag) => <option key={tag.id} value={tag.id}>{tag.name}</option>)}
            </select>
          </div>

          {(canCreateDocumentType || canDeleteDocumentType) && <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Manage document types</p>
            {canCreateDocumentType && <div className="flex gap-2">
              <Input value={newType} onChange={(event) => setNewType(event.target.value)} placeholder="e.g. purchase_order" />
              <Button type="button" variant="outline" disabled={!newType.trim()} onClick={() => void addType()}>Add type</Button>
            </div>}
            {canDeleteDocumentType && <div className="flex flex-wrap gap-2">
              {typeTags.map((tag) => <Button key={tag.id} type="button" size="sm" variant="outline" onClick={() => void removeType(tag)}>Remove {tag.name}</Button>)}
            </div>}
            {typeError && <p role="alert" className="text-sm text-red-600">{typeError}</p>}
          </div>}

          <div className="space-y-2">
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Find labels</p>
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
            <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Create and add a new label</p>
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
                {tagsForDisplay(selectedTags).map((tag) => (
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
                await onSave({ tags: selectedTags, dueDate: dueDate || null, documentTypeTagId: documentTypeTagId || null });
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
