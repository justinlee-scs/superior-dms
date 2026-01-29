import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, X, Check } from "lucide-react";
import { useDrop } from "react-dnd";
import { NativeTypes } from "react-dnd-html5-backend";
import { Button } from "@/app/components/ui/button";

interface UploadZoneProps {
  onFileUploaded: (file: File) => Promise<void>;
  darkMode?: boolean;
}

type UploadedFile = {
  file: File;
  status: "uploading" | "success" | "error";
};

export function UploadZone({ onFileUploaded, darkMode }: UploadZoneProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const dropRef = useRef<HTMLDivElement>(null);

  const uploadFile = async (file: File) => {
    setUploadedFiles((prev) => [
      ...prev,
      { file, status: "uploading" },
    ]);

    try {
      await onFileUploaded(file);

      setUploadedFiles((prev) =>
        prev.map((f) =>
          f.file === file ? { ...f, status: "success" } : f
        )
      );
    } catch {
      setUploadedFiles((prev) =>
        prev.map((f) =>
          f.file === file ? { ...f, status: "error" } : f
        )
      );
    }
  };

  const handleFiles = async (files: File[]) => {
    for (const file of files) {
      uploadFile(file);
    }
  };

  const handleDrop = useCallback(
    (item: { files: File[] }) => {
      handleFiles(Array.from(item.files));
    },
    []
  );

  const [{ isOver, canDrop }, drop] = useDrop(
    () => ({
      accept: [NativeTypes.FILE],
      drop: handleDrop,
      collect: (monitor) => ({
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
      }),
    }),
    [handleDrop]
  );

  useEffect(() => {
    if (dropRef.current) drop(dropRef);
  }, [drop]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    handleFiles(Array.from(e.target.files));
    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      <div
        ref={dropRef}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${darkMode
          ? isOver && canDrop
            ? "border-blue-500 bg-blue-900"
            : "border-black bg-gray-900"
          : isOver && canDrop
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-white"
          }`}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>
          Drag and drop files here, or{" "}
          <label className="text-blue-600 cursor-pointer underline">
            browse
            <input
              type="file"
              multiple
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Uploaded Files</h3>

          {uploadedFiles.map(({ file, status }, index) => (
            <div
              key={`${file.name}-${index}`}
              className={`flex items-center justify-between p-3 rounded-lg ${darkMode
                  ? "bg-gray-800 text-gray-100"
                  : "bg-gray-50 text-gray-900"
                }`}
            >
              <div className="flex items-center gap-3">
                {status === "uploading" && (
                  <Upload className="w-4 h-4 text-gray-400 animate-pulse" />
                )}
                {status === "success" && (
                  <Check className="w-4 h-4 text-green-500" />
                )}
                {status === "error" && (
                  <X className="w-4 h-4 text-red-500" />
                )}

                <div>
                  <p className="text-sm">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>

              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeFile(index)}
                disabled={status === "uploading"}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
