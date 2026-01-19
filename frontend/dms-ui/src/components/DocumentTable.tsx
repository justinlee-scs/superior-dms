import type { DocumentResponse } from "../api/documents";

interface Props {
  documents: DocumentResponse[];
}

export default function DocumentTable({ documents }: Props) {
  return (
    <table
      width="100%"
      style={{
        borderCollapse: "collapse",
        fontSize: 14,
      }}
    >
      <thead>
        <tr style={{ backgroundColor: "#f8fafc" }}>
          <Th>Filename</Th>
          <Th>Status</Th>
          <Th>Type</Th>
          <Th align="right">Confidence</Th>
        </tr>
      </thead>
      <tbody>
        {documents.map(d => (
          <tr key={d.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
            <Td>{d.filename}</Td>
            <Td>{d.status ?? "—"}</Td>
            <Td>{d.document_type ?? "—"}</Td>
            <Td align="right">
              {d.confidence != null ? d.confidence.toFixed(2) : "—"}
            </Td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Th({ children, align = "left" }: any) {
  return (
    <th
      style={{
        textAlign: align,
        padding: "10px 8px",
        fontWeight: 600,
        color: "#334155",
      }}
    >
      {children}
    </th>
  );
}

function Td({ children, align = "left" }: any) {
  return (
    <td
      style={{
        textAlign: align,
        padding: "10px 8px",
        color: "#0f172a",
      }}
    >
      {children}
    </td>
  );
}
