import { useEffect, useState } from "react";
import { fetchDocuments, type DocumentResponse } from "../api/documents";
import DocumentUpload from "../components/DocumentUpload";
import DocumentTable from "../components/DocumentTable";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadDocuments() {
    const data = await fetchDocuments();
    setDocuments(data);
  }

  async function handleUpload(file: File) {
    setLoading(true);
    await fetchDocuments(); // or uploadDocument(file) if wired
    await loadDocuments();
    setLoading(false);
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  return (
    <>
      <DocumentUpload onUploadComplete={loadDocuments} />
      {loading && <p>Loading…</p>}
      <hr />
      <DocumentTable documents={documents} />
    </>
  );
}
