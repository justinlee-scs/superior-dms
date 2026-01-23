import { useCallback, useState } from "react";
import { Upload, X } from "lucide-react";
import { useDrop } from "react-dnd";
import { NativeTypes } from "react-dnd-html5-backend";
import { Button } from "@/app/components/ui/button";

interface UploadZoneProps {
  onFilesUploaded: (files: File[]) => void;
}

export function UploadZone({ onFilesUploaded }: UploadZoneProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleDrop = useCallback(
    (item: { files: File[] }) => {
      const files = Array.from(item.files);
      setUploadedFiles((prev) => [...prev, ...files]);
      onFilesUploaded(files);
    },
    [onFilesUploaded]
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

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setUploadedFiles((prev) => [...prev, ...files]);
      onFilesUploaded(files);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const isActive = isOver && canDrop;

  return (
    <div className="space-y-4">
      <div
        ref={drop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
        }`}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p className="mb-2">
          Drag and drop files here, or{" "}
          <label className="text-blue-600 hover:underline cursor-pointer">
            browse
            <input
              type="file"
              multiple
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </p>
        <p className="text-sm text-gray-500">
          Supports all document types
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-medium text-sm">Uploaded Files</h3>
          {uploadedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <Upload className="w-4 h-4 text-green-600" />
                <div>
                  <p className="text-sm">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFile(index)}
                className="h-8 w-8 p-0"
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
