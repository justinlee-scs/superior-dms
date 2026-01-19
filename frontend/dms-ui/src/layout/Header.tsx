interface HeaderProps {
  onUpload: (file: File) => void;
  loading: boolean;
}

export default function Header({ onUpload, loading }: HeaderProps) {
  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return;
    onUpload(e.target.files[0]);
    e.target.value = "";
  }

  return (
    <header
      style={{
        height: 64,
        padding: "0 24px",
        borderBottom: "1px solid #e5e7eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "#ffffff",
      }}
    >
      <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>
        Documents
      </h1>

      <label
        style={{
          padding: "8px 14px",
          backgroundColor: "#2563eb",
          color: "#ffffff",
          borderRadius: 6,
          fontSize: 14,
          cursor: loading ? "not-allowed" : "pointer",
          opacity: loading ? 0.7 : 1,
        }}
      >
        {loading ? "Uploading…" : "Upload document"}
        <input
          type="file"
          hidden
          disabled={loading}
          onChange={handleFile}
        />
      </label>
    </header>
  );
}
