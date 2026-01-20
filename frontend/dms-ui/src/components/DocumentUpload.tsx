import { useState } from "react";
import { uploadDocument } from "../api/documents";

interface Props {
  onUploadComplete?: () => void;
}

export default function DocumentUpload({ onUploadComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  async function handleUpload() {
    if (!file) return;

    setStatus("Uploading...");

    try {
      await uploadDocument(file);
      setStatus("Processed");
      onUploadComplete?.();
    } catch (e: any) {
      if (e?.status === 409) {
        // Document already exists — this is OK
        setStatus("Already uploaded");
        onUploadComplete?.();
        return;
      }

      setStatus(e?.message ?? "Upload failed");
    }
  }

  return (
    <div>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={handleUpload}>Upload</button>
      <div>{status}</div>
    </div>
  );
}
