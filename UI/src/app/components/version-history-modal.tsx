import { useEffect, useMemo, useRef, useState } from "react";
import { Clock3, Download, Eye, Trash2, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/app/components/ui/button";
import type { Document } from "@/app/components/document-card";
import { getMyAccess } from "@/lib/rbac";
import {
  deleteDocumentVersion,
  downloadDocumentVersion,
  listDocumentVersions,
  previewDocumentVersion,
  setCurrentDocumentVersion,
  uploadDocumentVersion,
  type DocumentVersion,
} from "@/lib/dms";

interface VersionHistoryModalProps {
  open: boolean;
  document: Document | null;
  onClose: () => void;
  onUpdated: () => Promise<void>;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

export function VersionHistoryModal({
  open,
  document,
  onClose,
  onUpdated,
}: VersionHistoryModalProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [settingCurrentId, setSettingCurrentId] = useState<string | null>(null);
  const [deletingVersionId, setDeletingVersionId] = useState<string | null>(null);
  const [canPreviewVersion, setCanPreviewVersion] = useState(false);
  const [canDeleteVersion, setCanDeleteVersion] = useState(false);

  const sortedVersions = useMemo(
    () => [...versions].sort((a, b) => b.version_number - a.version_number),
    [versions],
  );

  useEffect(() => {
    if (!open || !document) return;
    setLoading(true);
    listDocumentVersions(document.id)
      .then(setVersions)
      .catch(() => toast.error("Failed to load version history"))
      .finally(() => setLoading(false));
  }, [open, document]);

  useEffect(() => {
    getMyAccess()
      .then((access) => {
        setCanPreviewVersion(access.permissions.includes("document_version.preview"));
        setCanDeleteVersion(access.permissions.includes("document_version.delete"));
      })
      .catch(() => {
        setCanPreviewVersion(false);
        setCanDeleteVersion(false);
      });
  }, []);

  if (!open || !document) return null;

  const onUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocumentVersion(document.id, file);
      const fresh = await listDocumentVersions(document.id);
      setVersions(fresh);
      await onUpdated();
      toast.success("New version uploaded");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Version upload failed",
      );
    } finally {
      setUploading(false);
    }
  };

  // Keep version download behavior aligned with regular document download flow.
  const onDownloadVersion = async (version: DocumentVersion) => {
    try {
      const blob = await downloadDocumentVersion(document.id, version.id);
      const url = window.URL.createObjectURL(blob);

      const a = window.document.createElement("a");
      a.href = url;

      a.download = document.name;

      window.document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Download failed");
    }
  };

  const onSetCurrent = async (version: DocumentVersion) => {
    setSettingCurrentId(version.id);
    try {
      await setCurrentDocumentVersion(document.id, version.id);
      const fresh = await listDocumentVersions(document.id);
      setVersions(fresh);
      await onUpdated();
      toast.success(`v${version.version_number} is now current`);
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to set current version",
      );
    } finally {
      setSettingCurrentId(null);
    }
  };

  const onPreviewVersion = async (version: DocumentVersion) => {
    try {
      const blob = await previewDocumentVersion(document.id, version.id);
      const url = window.URL.createObjectURL(blob);
      const previewWindow = window.open(url, "_blank");
      if (!previewWindow) toast.error("Popup blocked");
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Preview failed");
    }
  };

  const onDeleteVersion = async (version: DocumentVersion) => {
    const ok = window.confirm(
      `Delete version v${version.version_number}? This cannot be undone.`,
    );
    if (!ok) return;
    setDeletingVersionId(version.id);
    try {
      await deleteDocumentVersion(document.id, version.id);
      const fresh = await listDocumentVersions(document.id);
      setVersions(fresh);
      await onUpdated();
      toast.success(`Deleted v${version.version_number}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Delete failed");
    } finally {
      setDeletingVersionId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4">
      <div className="w-full max-w-2xl rounded-xl border bg-white shadow-xl">
        <div className="flex items-start justify-between border-b px-6 py-4">
          <div>
            <div className="flex items-center gap-2 text-2xl font-semibold">
              <Clock3 className="h-5 w-5 text-blue-600" />
              Version History
            </div>
            <div className="mt-2 text-lg text-gray-700">{document.name}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 hover:bg-gray-100"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="flex items-center justify-between px-6 py-4">
          <div className="text-sm text-gray-600">
            {versions.length} version(s)
          </div>
          <div>
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void onUpload(file);
                event.currentTarget.value = "";
              }}
            />
            <Button
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
              className="bg-slate-900 hover:bg-slate-800"
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload New Version
            </Button>
          </div>
        </div>

        <div className="max-h-[460px] overflow-auto px-6 pb-6">
          {loading && (
            <div className="py-8 text-center text-sm text-gray-500">
              Loading versions...
            </div>
          )}
          {!loading && sortedVersions.length === 0 && (
            <div className="py-8 text-center text-sm text-gray-500">
              No versions found
            </div>
          )}

          <div className="space-y-4">
            {sortedVersions.map((version, index) => {
              const isCurrent = version.is_current;
              return (
                <div key={version.id} className="relative pl-16">
                  {index < sortedVersions.length - 1 && (
                    <div className="absolute left-[22px] top-10 h-[calc(100%+8px)] w-px bg-gray-200" />
                  )}

                  <div
                    className={`absolute left-0 top-2 flex h-11 w-11 items-center justify-center rounded-full text-sm font-semibold ${
                      isCurrent
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    v{version.version_number}
                  </div>

                  <div
                    className={`rounded-xl border px-4 py-3 ${
                      isCurrent
                        ? "border-blue-200 bg-blue-50/70"
                        : "border-gray-200 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <div className="text-lg font-semibold">
                          v{version.version_number}
                        </div>
                        {isCurrent && (
                          <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={
                            isCurrent || settingCurrentId === version.id
                          }
                          onClick={() => void onSetCurrent(version)}
                        >
                          {isCurrent
                            ? "Current"
                            : settingCurrentId === version.id
                              ? "Setting..."
                              : "Set Current"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => void onDownloadVersion(version)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        {canPreviewVersion && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => void onPreviewVersion(version)}
                            title="Preview version"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                        {canDeleteVersion && (
                          <Button
                            variant="ghost"
                            size="icon"
                            disabled={
                              deletingVersionId === version.id ||
                              sortedVersions.length <= 1
                            }
                            onClick={() => void onDeleteVersion(version)}
                            title="Delete version"
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        )}
                      </div>
                    </div>

                    <div className="mt-2 text-sm text-gray-600">
                      Upload date:{" "}
                      {new Date(version.created_at).toLocaleString()} ·{" "}
                      {formatBytes(version.size_bytes)}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      Status: {version.processing_status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
