import { useState } from "react";
import { uploadDocument, type DocumentType } from "../api/documents";

interface Props {
  onUploadComplete?: () => void;
}

export default function DocumentUpload({ onUploadComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] =
    useState<DocumentType>("document");
  const [status, setStatus] = useState("");

  async function handleUpload() {
    if (!file) return;

    try {
      setStatus("Uploading...");
      await uploadDocument(file, documentType);
      setStatus("Processed");
      onUploadComplete?.();
    } catch (e: any) {
      setStatus(e.message ?? "Upload failed");
    }
  }

  return (
    <div>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <select
        value={documentType}
        onChange={(e) =>
          setDocumentType(e.target.value as DocumentType)
        }
      >
        <option value="document">Document</option>
        <option value="statement">Statement</option>
        <option value="outgoing_invoice">Outgoing Invoice</option>
        <option value="incoming_invoice">Incoming Invoice</option>
        <option value="contract">Contract</option>
        <option value="payroll">Payroll</option>
        <option value="manual">Manual</option>
        <option value="receipt">Receipt</option>
        <option value="other">Other</option>
      </select>

      <button onClick={handleUpload}>Upload</button>

      <div>{status}</div>
    </div>
  );
}
