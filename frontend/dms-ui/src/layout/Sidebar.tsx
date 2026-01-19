export default function Sidebar() {
  return (
    <aside
      style={{
        width: 240,
        backgroundColor: "#0b1220",
        color: "#e5e7eb",
        padding: "20px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 32,
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 600 }}>
        Document Manager
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <NavItem label="Documents" active />
        <NavItem label="Upload" />
        <NavItem label="Settings" />
      </nav>
    </aside>
  );
}

function NavItem({ label, active = false }: { label: string; active?: boolean }) {
  return (
    <div
      style={{
        padding: "8px 12px",
        borderRadius: 6,
        backgroundColor: active ? "#1e293b" : "transparent",
        cursor: "pointer",
        fontSize: 14,
      }}
    >
      {label}
    </div>
  );
}
