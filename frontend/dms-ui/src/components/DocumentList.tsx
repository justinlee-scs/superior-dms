import { useEffect, useState } from "react";
import { listDocuments, type DocumentResponse } from "../api/documents";

export default function DocumentList() {
  const [docs, setDocs] = useState<DocumentResponse[]>([]);

  useEffect(() => {
    listDocuments().then(setDocs);
  }, []);

  return (
    <ul>
      {docs.map((d) => (
        <li key={d.id}>
          {d.filename} — {d.status}
        </li>
      ))}
    </ul>
  );
}
