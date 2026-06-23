import { useEffect, useState } from "react";
import { PDFAnnotator } from "@/app/components/pdf-annotator";
import type { Document } from "@/app/components/document-card";
import { uploadDocumentVersion } from "@/lib/dms";
import { API_BASE_URL } from "@/lib/api";
import { toast } from "sonner";

interface PDFAnnotationModalProps {
  open: boolean;
  document: Document | null;
  onClose: () => void;
  onVersionSaved?: () => Promise<void>;
  darkMode?: boolean;
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

export function PDFAnnotationModal({
  open,
  document,
  onClose,
  onVersionSaved,
  darkMode = false,
}: PDFAnnotationModalProps) {
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !document) return;

    setLoading(true);
    const loadPdf = async () => {
      try {
        const token = sessionStorage.getItem("access_token");
        const res = await fetch(
          `${API_BASE_URL}/documents/${document.id}/preview`,
          {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          }
        );

        if (res.status === 401) {
          sessionStorage.removeItem("access_token");
          window.location.reload();
          return;
        }

        if (!res.ok) {
          throw new Error("Failed to load PDF");
        }

        const blob = await res.blob();
        setPdfBlob(blob);
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

  const handleSaveVersion = async (annotatedPdfBlob: Blob) => {
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
      await uploadDocumentVersion(document.id, file);

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
        className={`fixed inset-0 z-50 flex items-center justify-center ${
          darkMode ? "bg-black/80" : "bg-black/50"
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
    <div className="fixed inset-0 z-50">
      <PDFAnnotator
        document={document}
        pdfBlob={pdfBlob}
        onClose={onClose}
        onSaveVersion={handleSaveVersion}
        darkMode={darkMode}
        currentUserName={getCurrentUserName()}
      />
    </div>
  );
}