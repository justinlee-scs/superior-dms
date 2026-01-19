import { useEffect, useState } from "react";

import Sidebar from "./layout/Sidebar";
import Header from "./layout/Header";
import DocumentTable from "./components/DocumentTable";

import {
  fetchDocuments,
  uploadDocument,
  type DocumentResponse,
} from "./api/documents";

export default function App() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(false);

  async function loadDocuments() {
    const data = await fetchDocuments();
    setDocuments(data);
  }

  async function handleUpload(file: File) {
    setLoading(true);
    await uploadDocument(file);
    await loadDocuments();
    setLoading(false);
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar />

      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Header onUpload={handleUpload} loading={loading} />

        <main style={{ padding: "24px", overflow: "auto" }}>
          <DocumentTable documents={documents} />
        </main>
      </div>
    </div>
  );
}
