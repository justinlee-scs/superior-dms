import { useEffect, useMemo, useState } from "react";
import { PDFAnnotator } from "@/app/components/pdf-annotator";
import type { Document } from "@/app/components/document-card";
import { getDocumentOutput, uploadDocumentVersion } from "@/lib/dms";
import { getMyAccess } from "@/lib/rbac";
import { API_BASE_URL } from "@/lib/api";
import { toast } from "sonner";
import { Badge } from "@/app/components/ui/badge";
import { Input } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";

interface PDFAnnotationModalProps {
  open: boolean;
  document: Document | null;
  onClose: () => void;
  onVersionSaved?: () => Promise<void>;
  darkMode?: boolean;
  availableTags?: string[];
  onSaveTags?: (payload: { tags: string[]; dueDate: string | null }) => Promise<void>;
}

// Reads the cached user object that ProfileDialog (and login) stores in
// sessionStorage under "user", and pulls out a display name for stamps.
// Falls back to email, then a generic label, if username isn't set.
function getCurrentUserName(): string {
  try {
    const raw = sessionStorage.getItem("user");
    if (!raw) return "Unknown User";
    const user = JSON.parse(raw);
    return user.full_name || user.username || user.email || "Unknown User";
  } catch {
    return "Unknown User";
  }
}

type AnnotationLayoutJson = {
  customStamps?: string[];
};

function TagEditorInline({
  document,
  availableTags,
  onSave,
  darkMode,
}: {
  document: Document | null;
  availableTags: string[];
  onSave: (payload: { tags: string[]; dueDate: string | null }) => Promise<void>;
  darkMode?: boolean;
}) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");
  const [searchTag, setSearchTag] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSelectedTags(document?.tags ?? []);
    setDueDate(document?.dueDate ?? "");
  }, [document]);

  const visiblePool = useMemo(() => {
    if (!searchTag.trim()) return availableTags;
    const q = searchTag.trim().toLowerCase();
    return availableTags.filter((t) => t.toLowerCase().includes(q));
  }, [availableTags, searchTag]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const addNewTag = () => {
    const normalized = newTag.trim().toLowerCase().replace(/\s+/g, "_");
    if (!normalized) return;
    setSelectedTags((prev) => prev.includes(normalized) ? prev : [...prev, normalized]);
    setNewTag("");
  };

  return (
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
        <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Search tags</p>
        <Input
          value={searchTag}
          onChange={(e) => setSearchTag(e.target.value)}
          placeholder="Search existing tags..."
          className={darkMode ? "bg-gray-800 border-gray-700 text-white placeholder:text-gray-500" : ""}
        />
      </div>

      <div className="space-y-2">
        <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Tag pool</p>
        <div className={`max-h-48 overflow-auto rounded-md border p-2 ${darkMode ? "border-gray-700 bg-gray-800" : ""}`}>
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
        <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Add new tag</p>
        <div className="flex gap-2">
          <Input
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            placeholder="e.g. project:apollo"
            className={darkMode ? "bg-gray-800 border-gray-700 text-white placeholder:text-gray-500" : ""}
            onKeyDown={(e) => { if (e.key === "Enter") addNewTag(); }}
          />
          <Button type="button" variant="outline" onClick={addNewTag} disabled={!newTag.trim()}
            className={darkMode ? "border-gray-600 text-gray-300 hover:bg-gray-700" : ""}
          >
            Add
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <p className={`text-sm font-medium ${darkMode ? "text-gray-300" : ""}`}>Selected</p>
        <div className={`rounded-md border p-2 min-h-12 ${darkMode ? "border-gray-700 bg-gray-800" : ""}`}>
          <div className="flex flex-wrap gap-2">
            {selectedTags.map((tag) => (
              <Badge key={tag} className="cursor-pointer" onClick={() => toggleTag(tag)}>
                {tag} ✕
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <Button
        className="w-full"
        disabled={saving}
        onClick={async () => {
          setSaving(true);
          try {
            await onSave({ tags: selectedTags, dueDate: dueDate || null });
          } finally {
            setSaving(false);
          }
        }}
      >
        {saving ? "Saving..." : "Save Tags"}
      </Button>
    </div>
  );
}

export function PDFAnnotationModal({
  open,
  document,
  onClose,
  onVersionSaved,
  darkMode = false,
  availableTags = [],
  onSaveTags,
}: PDFAnnotationModalProps) {
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [layoutJson, setLayoutJson] = useState<AnnotationLayoutJson | null>(null);
  const [loading, setLoading] = useState(false);
  const [canAccessStamps, setCanAccessStamps] = useState(false);
  const [canCreateStampLabels, setCanCreateStampLabels] = useState(false);
  const [canAccessTextBoxes, setCanAccessTextBoxes] = useState(false);
  const [tagPanelOpen, setTagPanelOpen] = useState(false);

  useEffect(() => {
    getMyAccess()
      .then((access) => {
        setCanAccessStamps(access.permissions.includes("document_version.stamp_access"));
        setCanCreateStampLabels(
          access.permissions.includes("document_version.stamp_label_create"),
        );
        setCanAccessTextBoxes(
          access.permissions.includes("document_version.text_box_access"),
        );
      })
      .catch(() => {
        setCanAccessStamps(false);
        setCanCreateStampLabels(false);
        setCanAccessTextBoxes(false);
      });
  }, []);

  useEffect(() => {
    if (!open || !document) return;

    setLoading(true);
    const loadPdf = async () => {
      try {
        const token = sessionStorage.getItem("access_token");
        const [previewResponse, outputResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/documents/${document.id}/preview`, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          }),
          getDocumentOutput(document.id),
        ]);

        if (previewResponse.status === 401) {
          sessionStorage.removeItem("access_token");
          window.location.reload();
          return;
        }

        if (!previewResponse.ok) {
          throw new Error("Failed to load PDF");
        }

        const blob = await previewResponse.blob();
        setPdfBlob(blob);
        setLayoutJson(
          outputResponse.layout_json &&
            typeof outputResponse.layout_json === "object"
            ? (outputResponse.layout_json as AnnotationLayoutJson)
            : null,
        );
      } catch (error) {
        toast.error("Failed to load PDF for annotation");
        console.error(error);
        onClose();
      } finally {
        setLoading(false);
      }
    };

    loadPdf();
  }, [open, document, onClose]);

  const handleSaveVersion = async (
    annotatedPdfBlob: Blob,
    annotatorLayoutJson?: { customStamps?: string[] },
  ) => {
    if (!document) return;

    try {
      // The blob coming from PDFAnnotator is now a real, multi-page
      // application/pdf (built with pdf-lib from the rendered pages +
      // baked-in annotation layers), not a flattened single-page PNG.
      // Keep the original filename/extension so it reads as a proper new
      // version of the same document rather than a derived image export.
      const file = new File([annotatedPdfBlob], document.name, {
        type: "application/pdf",
      });

      // Upload as new version
      await uploadDocumentVersion(document.id, file, {
        customStamps: annotatorLayoutJson?.customStamps ?? layoutJson?.customStamps ?? [],
      });

      // Refresh document list if callback provided
      if (onVersionSaved) {
        await onVersionSaved();
      }

      toast.success("Annotated version saved successfully");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to save version"
      );
      throw error;
    }
  };

  if (!open || !document) return null;

  if (loading) {
    return (
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center ${darkMode ? "bg-black/80" : "bg-black/50"
          }`}
      >
        <div className={`rounded-lg p-6 ${darkMode ? "bg-gray-900" : "bg-white"}`}>
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-4 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
            <p className={darkMode ? "text-white" : "text-gray-900"}>
              Loading PDF...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!pdfBlob) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* PDF annotator — shrinks when tag panel is open */}
      <div className={`flex flex-col ${tagPanelOpen ? "flex-1 min-w-0" : "w-full"}`}>
        <PDFAnnotator
          document={document}
          pdfBlob={pdfBlob}
          onClose={onClose}
          onSaveVersion={handleSaveVersion}
          darkMode={darkMode}
          currentUserName={getCurrentUserName()}
          layoutJson={layoutJson}
          canAccessStamps={canAccessStamps}
          canCreateStampLabels={canCreateStampLabels}
          canAccessTextBoxes={canAccessTextBoxes}
          onEditTags={onSaveTags ? () => setTagPanelOpen(v => !v) : undefined}
        />
      </div>

      {/* Tag panel — slides in from the right */}
      {onSaveTags && tagPanelOpen && (
        <div className={`flex flex-col w-96 shrink-0 border-l overflow-y-auto ${darkMode ? "bg-gray-900 border-gray-700" : "bg-white border-gray-200"}`}>
          <div className={`flex items-center justify-between px-4 py-3 border-b ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
            <span className={`font-semibold ${darkMode ? "text-gray-100" : ""}`}>Edit Tags</span>
            <button
              onClick={() => setTagPanelOpen(false)}
              className={`flex items-center justify-center w-6 h-6 rounded-full border text-sm font-bold transition-colors ${darkMode ? "border-gray-600 bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white" : "border-gray-300 bg-white text-gray-500 hover:bg-gray-100 hover:text-gray-800"}`}
            >
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <TagEditorInline
              document={document}
              availableTags={availableTags}
              onSave={async (payload) => {
                await onSaveTags(payload);
              }}
              darkMode={darkMode}
            />
          </div>
        </div>
      )}
    </div>
  );
}
