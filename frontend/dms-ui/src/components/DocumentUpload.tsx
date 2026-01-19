import { useState } from "react";
import { uploadDocument } from "../api/documents";

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  async function handleUpload() {
    if (!file) return;

    try {
      setStatus("Uploading...");
      await uploadDocument(file);
      setStatus("Processed");
    } catch (e: any) {
      setStatus(e.message);
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
