import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import {
  getDashboard,
  getProvinces,
  getRegionalDistricts,
  getExpiringSoon,
  bulkToggleTracking,
  updateMunicipality,
  createMunicipality,
  createLicense,
  updateLicense,
  deleteLicense,
  getCompanies,
  addCompanyToLicense,
  removeCompanyFromLicense,
  type Company,
  type GovernmentLicenseRow,
  type Province,
  type RegionalDistrict,
  type DashboardStatusFilter,
  type LicenseStatus,
  type CreateLicensePayload,
} from "./licensing";

// ---------------------------------------------------------------------------
// Drop-in standalone page. Wire into your router as e.g.:
//   <Route path="/licensing" element={<LicensingPage />} />
// And see NavToggle.tsx for the nav switch snippet to drop into app.tsx.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// IMBL (Inter-Municipal Business License) eligibility config.
// Edit this list when new IMBL regions are established or membership changes.
// Source: Official BC municipal websites, verified July 2026.
// Key = display name for the IMBL region (shown in tooltip).
// Value = array of municipality names exactly as they appear in the seed data.
// A municipality with an eligible IMBL region but no intermunicipal license
// yet will show a yellow ✦ IMBL badge as a prompt to get one.
// ---------------------------------------------------------------------------
const IMBL_REGIONS: Record<string, string[]> = {
  // --- Lower Mainland ---
  "Metro West": [
    "Burnaby", "Delta", "New Westminster", "Richmond", "Surrey", "Vancouver",
  ],
  "Fraser Valley": [
    "Abbotsford", "Chilliwack", "Delta", "Harrison Hot Springs", "Hope",
    "Kent", "Langley",          // City of Langley
    "Langley",                  // Township = District Municipality named "Langley" in seed
    "Maple Ridge", "Mission", "Pitt Meadows", "Surrey",
  ],
  "Tri-Cities": [
    "Coquitlam", "Port Coquitlam", "Port Moody",
  ],
  "North Shore": [
    "North Vancouver",   // covers both City and District (both are in seed)
    "West Vancouver",
  ],
  "Sunshine Coast": [
    "Gibsons", "Sechelt", "shishalh Nation",
  ],

  // --- Vancouver Island ---
  "Greater Victoria": [
    "Central Saanich", "Colwood", "Esquimalt", "Highlands", "Langford",
    "Metchosin", "North Saanich", "Oak Bay", "Saanich", "Sidney",
    "Sooke", "Victoria", "View Royal",
  ],
  "Central Vancouver Island": [
    "Campbell River", "Comox", "Courtenay", "Cumberland", "Duncan",
    "Ladysmith", "Lake Cowichan", "Nanaimo", "North Cowichan",
    "Parksville", "Port Alberni", "Qualicum Beach",
  ],
  "Cowichan Valley": [
    "Duncan", "Ladysmith", "Lake Cowichan", "North Cowichan",
  ],
  "Comox Valley": [
    "Comox", "Courtenay",
  ],

  // --- Okanagan-Similkameen ---
  "Okanagan-Similkameen": [
    "Armstrong", "Coldstream", "Enderby", "Kelowna", "Keremeos",
    "Lake Country", "Lumby", "Merritt", "Oliver", "Osoyoos",
    "Peachland", "Penticton", "Princeton", "Revelstoke", "Salmon Arm",
    "Sicamous", "Spallumcheen", "Summerland", "Vernon", "West Kelowna",
  ],

  // --- Thompson-Nicola ---
  "Thompson-Nicola": [
    "Kamloops", "Merritt", "Barriere", "Clearwater", "Lillooet",
    "Logan Lake", "Chase",
  ],

  // --- Kootenays ---
  "Cranbrook / Kimberley": [
    "Cranbrook", "Kimberley",
  ],
  "Elk Valley": [
    "Elkford", "Fernie", "Sparwood",
  ],
  "Greater Trail": [
    "Fruitvale", "Montrose", "Rossland", "Trail", "Warfield",
  ],
  "Kootenay": [
    "Castlegar", "Creston", "Grand Forks", "Kaslo", "Nelson",
    "New Denver", "Rossland", "Salmo", "Silverton", "Slocan",
  ],

  // --- Northeast ---
  "Northeast BC": [
    "Chetwynd", "Dawson Creek", "Fort St. John", "Hudson's Hope",
    "Pouce Coupe", "Taylor", "Tumbler Ridge",
  ],
};

// Precomputed lookup: municipality name → IMBL region name (or null)
const IMBL_LOOKUP: Record<string, string> = {};
for (const [region, members] of Object.entries(IMBL_REGIONS)) {
  for (const m of members) {
    IMBL_LOOKUP[m] = region;
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortField = "municipality_name" | "region_name" | "computed_status" | "expiry_date" | "cost";
type SortDir = "asc" | "desc";
type CoverageFilter = "all" | "municipal" | "intermunicipal" | "no_license" | "imbl_eligible";

interface LicenseFormState {
  license_number: string;
  issue_date: string;
  expiry_date: string;
  cost: string;
  issuing_authority: string;
  notes: string;
  scope: "Municipal" | "Intermunicipal";
  status_override: LicenseStatus | "";
  company_ids: string[];
}

const emptyForm = (): LicenseFormState => ({
  license_number: "", issue_date: "", expiry_date: "",
  cost: "", issuing_authority: "", notes: "",
  scope: "Municipal", status_override: "",
  company_ids: [],
});

// ---------------------------------------------------------------------------
// Status styles — light and dark variants for each status badge
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, { bg: string; darkBg: string; fg: string; darkFg: string; dot: string }> = {
  "Active": { bg: "#EAF4EC", darkBg: "#1A3D28", fg: "#1F6B3A", darkFg: "#4ADE80", dot: "#2F9E50" },
  "Expiring Soon": { bg: "#FCF1DE", darkBg: "#3D2E0A", fg: "#92600C", darkFg: "#FBB03B", dot: "#E2A12E" },
  "Expired": { bg: "#FBEAEA", darkBg: "#3D1A1A", fg: "#9B2C2C", darkFg: "#F87171", dot: "#D14343" },
  "Inactive": { bg: "#EEEEF0", darkBg: "#2A2A2E", fg: "#5B5B66", darkFg: "#9CA3AF", dot: "#9494A0" },
  "Pending": { bg: "#EAEFFB", darkBg: "#1A2540", fg: "#2C4C9B", darkFg: "#93C5FD", dot: "#5478D1" },
  "No License": { bg: "#F6F4EF", darkBg: "#1F1F1F", fg: "#8A7F66", darkFg: "#6B7280", dot: "#C9BC9C" },
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({
  status, darkMode, clickable = false, onClick,
}: {
  status: string | null | undefined;
  darkMode: boolean;
  clickable?: boolean;
  onClick?: () => void;
}) {
  const key = status ?? "No License";
  const s = STATUS_STYLES[key] ?? STATUS_STYLES["No License"];
  return (
    <span
      onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: "3px 10px", borderRadius: 999,
        background: darkMode ? s.darkBg : s.bg,
        color: darkMode ? s.darkFg : s.fg,
        fontSize: 12.5, fontWeight: 600, whiteSpace: "nowrap",
        cursor: clickable ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.dot, flexShrink: 0 }} />
      {key}
      {clickable && <span style={{ fontSize: 10, opacity: 0.6, marginLeft: 2 }}>▾</span>}
    </span>
  );
}

function SortIcon({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDir }) {
  if (sortField !== field) return <span style={{ opacity: 0.3, marginLeft: 4 }}>↕</span>;
  return <span style={{ marginLeft: 4 }}>{sortDir === "asc" ? "↑" : "↓"}</span>;
}

// Inline confirm popover for tracking toggle — clicking "Enabled"/"Disabled"
// shows a small confirm popover rather than acting immediately.
function TrackingCell({
  row, darkMode, onToggle,
}: {
  row: GovernmentLicenseRow;
  darkMode: boolean;
  onToggle: (id: string, enabled: boolean) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const surface = darkMode ? "#1F2937" : "#FFFFFF";
  const border = darkMode ? "#374151" : "#E4DFD0";
  const text = darkMode ? "#F9FAFB" : "#2A2820";

  const handleConfirm = async () => {
    setLoading(true);
    await onToggle(row.municipality_id, !row.tracking_enabled);
    setLoading(false);
    setOpen(false);
  };

  return (
    <div style={{ position: "relative", display: "inline-block" }} ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          fontSize: 12.5, fontWeight: 600, cursor: "pointer",
          color: row.tracking_enabled ? "#2F9E50" : (darkMode ? "#6B7280" : "#A6A092"),
          background: "none", border: "none", padding: "2px 0",
          textDecoration: "underline dotted", textUnderlineOffset: 3,
        }}
      >
        {row.tracking_enabled ? "Enabled" : "Disabled"}
      </button>
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", left: 0, top: 28, zIndex: 50,
            background: surface, border: `1px solid ${border}`,
            borderRadius: 8, padding: 14, minWidth: 200,
            boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
          }}>
            <p style={{ fontSize: 13, color: text, margin: "0 0 12px", lineHeight: 1.4 }}>
              {row.tracking_enabled
                ? `Disable tracking for ${row.municipality_name}?`
                : `Enable tracking for ${row.municipality_name}?`}
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setOpen(false)}
                style={{ fontSize: 12.5, padding: "5px 12px", borderRadius: 6, border: `1px solid ${border}`, background: "none", cursor: "pointer", color: text }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading}
                style={{
                  fontSize: 12.5, padding: "5px 12px", borderRadius: 6, border: "none",
                  background: row.tracking_enabled ? "#D14343" : "#2F9E50",
                  color: "#fff", cursor: "pointer", fontWeight: 600,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? "…" : row.tracking_enabled ? "Disable" : "Enable"}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// Inline status override dropdown — clicking the badge opens a small dropdown
// to override the auto-calculated status. Only available when a license exists.
function StatusCell({
  row, darkMode, onStatusChange,
}: {
  row: GovernmentLicenseRow;
  darkMode: boolean;
  onStatusChange: (licenseId: string, status: LicenseStatus | null) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const surface = darkMode ? "#1F2937" : "#FFFFFF";
  const border = darkMode ? "#374151" : "#E4DFD0";
  const text = darkMode ? "#F9FAFB" : "#2A2820";
  const subtle = darkMode ? "#374151" : "#F4F2EC";

  // No license — show static badge, no interaction
  if (!row.license_id) {
    return <StatusBadge status={null} darkMode={darkMode} />;
  }

  const handlePick = async (status: LicenseStatus | null) => {
    setLoading(true);
    await onStatusChange(row.license_id!, status);
    setLoading(false);
    setOpen(false);
  };

  const statuses: (LicenseStatus | null)[] = [null, "Active", "Inactive", "Pending", "Expired"];
  const labels: Record<string, string> = {
    "null": "Auto (from expiry date)",
    "Active": "✅ Active",
    "Inactive": "⏸ Inactive",
    "Pending": "🕐 Pending",
    "Expired": "❌ Expired",
  };

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <StatusBadge
        status={row.computed_status}
        darkMode={darkMode}
        clickable={!loading}
        onClick={() => setOpen(o => !o)}
      />
      {open && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setOpen(false)} />
          <div style={{
            position: "absolute", left: 0, top: 32, zIndex: 50,
            background: surface, border: `1px solid ${border}`,
            borderRadius: 8, padding: "4px 0", minWidth: 200,
            boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
          }}>
            <div style={{ fontSize: 11, color: darkMode ? "#6B7280" : "#A6A092", padding: "6px 14px 4px", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>
              Override Status
            </div>
            {statuses.map(s => (
              <button
                key={String(s)}
                onClick={() => handlePick(s)}
                style={{
                  display: "block", width: "100%", textAlign: "left",
                  padding: "8px 14px", fontSize: 13, fontFamily: "inherit",
                  background: String(s) === String(row.status_override ?? null) ? subtle : "none",
                  border: "none", cursor: "pointer", color: text,
                }}
              >
                {labels[String(s)]}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// Blue badge for municipalities already covered by an intermunicipal license
function InterBadge({ darkMode }: { darkMode: boolean }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 7px", borderRadius: 999, fontSize: 11, fontWeight: 700,
      background: darkMode ? "#1A2540" : "#EAEFFB",
      color: darkMode ? "#93C5FD" : "#2C4C9B",
      marginLeft: 6, verticalAlign: "middle", letterSpacing: "0.02em",
    }}>
      🌐 INTER
    </span>
  );
}

// Yellow badge for municipalities eligible for an IMBL but not yet enrolled.
// Shows the IMBL region name in a tooltip on hover.
function ImblEligibleBadge({ regionName, darkMode }: { regionName: string; darkMode: boolean }) {
  const [hover, setHover] = useState(false);
  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", marginLeft: 6 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <span style={{
        display: "inline-flex", alignItems: "center", gap: 4,
        padding: "2px 7px", borderRadius: 999, fontSize: 11, fontWeight: 700,
        background: darkMode ? "#3D2E0A" : "#FEF9C3",
        color: darkMode ? "#FBB03B" : "#92600C",
        verticalAlign: "middle", letterSpacing: "0.02em",
        cursor: "default",
      }}>
        ✦ IMBL
      </span>
      {/* Tooltip showing which IMBL region this municipality belongs to */}
      {hover && (
        <span style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: "50%",
          transform: "translateX(-50%)",
          background: darkMode ? "#374151" : "#1F2937",
          color: "#F9FAFB", fontSize: 11.5, fontWeight: 500,
          padding: "5px 10px", borderRadius: 6, whiteSpace: "nowrap",
          pointerEvents: "none", zIndex: 60,
          boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
        }}>
          Eligible: {regionName}
        </span>
      )}
    </span>
  );
}

// CSV export — exports exactly the current filtered + sorted view
function exportCSV(rows: GovernmentLicenseRow[]) {
  const headers = [
    "Province", "Region", "Government", "Type", "Tracking",
    "IMBL Region", "License Scope", "License Number", "Coverage",
    "License Status", "Expiry Date", "Days Until Expiry", "Cost",
  ];
  const lines = rows.map(r => [
    r.province_name,
    r.region_name,
    r.municipality_name,
    r.municipality_type,
    r.tracking_enabled ? "Enabled" : "Disabled",
    IMBL_LOOKUP[r.municipality_name] ?? "",
    r.license_scope ?? "",
    r.license_number ?? "",
    r.covered_via_region ? "Intermunicipal" : r.license_id ? "Direct" : "None",
    r.computed_status ?? "No License",
    r.expiry_date ?? "",
    r.days_until_expiry != null ? String(r.days_until_expiry) : "",
    r.cost != null ? String(r.cost) : "",
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(","));

  const csv = [headers.join(","), ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `business-licenses-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LicensingPage({ darkMode = false }: { darkMode?: boolean }) {
  const [rows, setRows] = useState<GovernmentLicenseRow[]>([]);
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [regions, setRegions] = useState<RegionalDistrict[]>([]);
  const [expiringSoon, setExpiringSoon] = useState<GovernmentLicenseRow[]>([]);

  // Filters
  const [companies, setCompanies] = useState<Company[]>([]);
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<DashboardStatusFilter>("all");
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all");
  const [provinceFilter, setProvinceFilter] = useState<string>("");
  const [regionFilter, setRegionFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [showAllTracking, setShowAllTracking] = useState(false);

  // Sorting — separate from column header clicks, controlled by Sort by dropdown
  const [sortField, setSortField] = useState<SortField>("municipality_name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissedWarning, setDismissedWarning] = useState(false);

  // License add/edit modal
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [editingRow, setEditingRow] = useState<GovernmentLicenseRow | null>(null);
  const [form, setForm] = useState<LicenseFormState>(emptyForm());
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [addGovOpen, setAddGovOpen] = useState(false);

  // ---------------------------------------------------------------------------
  // Theme tokens — all colours derived from darkMode prop so the page
  // respects the DMS-wide dark mode toggle automatically.
  // ---------------------------------------------------------------------------
  const bg = darkMode ? "#111827" : "#FBFAF7";
  const surface = darkMode ? "#1F2937" : "#FFFFFF";
  const border = darkMode ? "#374151" : "#E4DFD0";
  const text = darkMode ? "#F9FAFB" : "#2A2820";
  const muted = darkMode ? "#9CA3AF" : "#7A7460";
  const subtle = darkMode ? "#374151" : "#F4F2EC";
  const inputBg = darkMode ? "#374151" : "#FFFFFF";
  const inputBorder = darkMode ? "#4B5563" : "#DBD6C8";
  const accent = darkMode ? "#D97706" : "#A1944F";

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [companiesData, provincesData, regionsData, dashboardData, expiringData] = await Promise.all([
        getCompanies(),
        getProvinces(),
        getRegionalDistricts(),
        getDashboard({
          statusFilter,
          provinceId: provinceFilter || undefined,
          regionalDistrictId: regionFilter || undefined,
          search: search || undefined,
          trackingEnabledOnly: !showAllTracking,
          companyId: activeCompanyId || undefined,
        }),
        getExpiringSoon(30),
      ]);
      setCompanies(companiesData);
      setProvinces(provincesData);
      setRegions(regionsData);
      setRows(dashboardData);
      setExpiringSoon(expiringData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load licensing data.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, provinceFilter, regionFilter, search, showAllTracking, activeCompanyId]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // ---------------------------------------------------------------------------
  // Derived / memoized values
  // ---------------------------------------------------------------------------

  // Region dropdown filtered to selected province
  const filteredRegions = useMemo(() => {
    const sorted = [...regions].sort((a, b) => a.name.localeCompare(b.name));
    if (!provinceFilter) return sorted;
    return sorted.filter(r => r.province_id === provinceFilter);
  }, [regions, provinceFilter]);

  // Coverage + IMBL filter applied client-side after dashboard data loads
  const filteredRows = useMemo(() => {
    switch (coverageFilter) {
      case "no_license": return rows.filter(r => !r.license_id);
      case "intermunicipal": return rows.filter(r => r.covered_via_region);
      case "municipal": return rows.filter(r => r.license_id && !r.covered_via_region);
      // IMBL eligible = in an IMBL region AND not already covered by intermunicipal
      case "imbl_eligible": return rows.filter(r => IMBL_LOOKUP[r.municipality_name] && !r.covered_via_region);
      default: return rows;
    }
  }, [rows, coverageFilter]);

  // Sorting applied last. Cost sort hides municipalities with no license (no cost data).
  const sortedRows = useMemo(() => {
    let base = filteredRows;

    // When sorting by cost, hide rows with no license (no cost to compare)
    if (sortField === "cost") {
      base = base.filter(r => r.license_id && r.cost != null);
    }

    return [...base].sort((a, b) => {
      let av: string | number = "", bv: string | number = "";
      switch (sortField) {
        case "municipality_name": av = a.municipality_name; bv = b.municipality_name; break;
        case "region_name": av = a.region_name; bv = b.region_name; break;
        case "computed_status": av = a.computed_status ?? ""; bv = b.computed_status ?? ""; break;
        case "expiry_date": av = a.expiry_date ?? ""; bv = b.expiry_date ?? ""; break;
        case "cost": av = a.cost ?? 0; bv = b.cost ?? 0; break;
      }
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [filteredRows, sortField, sortDir]);

  // Summary counts for the header stat row
  const counts = useMemo(() => {
    const c = { active: 0, expiringSoon: 0, expired: 0, noLicense: 0 };
    for (const r of rows) {
      if (r.computed_status === "Active") c.active++;
      else if (r.computed_status === "Expiring Soon") c.expiringSoon++;
      else if (r.computed_status === "Expired") c.expired++;
      else if (!r.computed_status) c.noLicense++;
    }
    return c;
  }, [rows]);

  // Coverage pill counts — always reflect full (unfiltered) row set
  const coverageCounts = useMemo(() => ({
    direct: rows.filter(r => r.license_id && !r.covered_via_region).length,
    inter: rows.filter(r => r.covered_via_region).length,
    none: rows.filter(r => !r.license_id).length,
    imblEligible: rows.filter(r => IMBL_LOOKUP[r.municipality_name] && !r.covered_via_region).length,
  }), [rows]);

  // ---------------------------------------------------------------------------
  // Action handlers
  // ---------------------------------------------------------------------------

  // Inline tracking toggle (per municipality)
  const handleTrackingToggle = async (municipalityId: string, enabled: boolean) => {
    await updateMunicipality(municipalityId, { tracking_enabled: enabled });
    loadAll();
  };

  // Inline license status override (per license)
  const handleStatusChange = async (licenseId: string, status: LicenseStatus | null) => {
    await updateLicense(licenseId, { status_override: status ?? undefined });
    loadAll();
  };

  // Bulk toggle all municipalities in a region
  const handleRegionBulkToggle = async (regionId: string, enabled: boolean) => {
    await bulkToggleTracking({ regional_district_id: regionId, tracking_enabled: enabled });
    loadAll();
  };

  // Bulk toggle all municipalities in a province
  const handleProvinceBulkToggle = async (provinceId: string, enabled: boolean) => {
    await bulkToggleTracking({ province_id: provinceId, tracking_enabled: enabled });
    loadAll();
  };

  // Open the add/edit modal, pre-filling form if a license already exists
  const openEdit = (row: GovernmentLicenseRow) => {
    setEditingRow(row);
    setFormError(null);
    setForm(row.license_id ? {
      license_number: row.license_number ?? "",
      issue_date: "",
      expiry_date: row.expiry_date ?? "",
      cost: row.cost != null ? String(row.cost) : "",
      issuing_authority: "",
      notes: "",
      scope: row.license_scope ?? "Municipal",
      status_override: row.status_override ?? "",
      company_ids: row.company_ids ?? [],
    } : emptyForm());
    setMenuOpenId(null);
  };

  const handleFormSave = async () => {
    if (!editingRow) return;
    if (!form.expiry_date) { setFormError("Expiry date is required."); return; }
    setFormLoading(true);
    setFormError(null);
    try {
      if (editingRow.license_id) {
        // Update existing license
        await updateLicense(editingRow.license_id, {
          license_number: form.license_number || undefined,
          expiry_date: form.expiry_date,
          issue_date: form.issue_date || undefined,
          cost: form.cost ? parseFloat(form.cost) : undefined,
          issuing_authority: form.issuing_authority || undefined,
          notes: form.notes || undefined,
          status_override: (form.status_override as LicenseStatus) || undefined,
        });
        // Sync company assignments — diff current vs desired
        const current = editingRow.company_ids ?? [];
        const desired = form.company_ids;
        const toAdd = desired.filter(id => !current.includes(id));
        const toRemove = current.filter(id => !desired.includes(id));
        await Promise.all([
          ...toAdd.map(id => addCompanyToLicense(editingRow.license_id!, id)),
          ...toRemove.map(id => removeCompanyFromLicense(editingRow.license_id!, id)),
        ]);
      } else {
        // Create new license — scope determines whether to attach to
        // municipality_id (Municipal) or regional_district_id (Intermunicipal)
        const payload: CreateLicensePayload = {
          scope: form.scope,
          expiry_date: form.expiry_date,
          license_number: form.license_number || undefined,
          issue_date: form.issue_date || undefined,
          cost: form.cost ? parseFloat(form.cost) : undefined,
          issuing_authority: form.issuing_authority || undefined,
          notes: form.notes || undefined,
          status_override: (form.status_override as LicenseStatus) || undefined,
        };
        if (form.scope === "Municipal") {
          payload.municipality_id = editingRow.municipality_id;
        } else {
          const region = regions.find(r => r.name === editingRow.region_name);
          if (region) payload.regional_district_id = region.id;
        }
        const created = await createLicense(payload);
        // Assign companies to the newly created license
        await Promise.all(
          form.company_ids.map(id => addCompanyToLicense(created.id, id))
        );
      }
      setEditingRow(null);
      loadAll();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Failed to save license.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteLicense = async (row: GovernmentLicenseRow) => {
    if (!row.license_id) return;
    if (!confirm(`Remove license from ${row.municipality_name}?`)) return;
    await deleteLicense(row.license_id);
    setMenuOpenId(null);
    loadAll();
  };

  // ---------------------------------------------------------------------------
  // Shared style helpers
  // ---------------------------------------------------------------------------

  const thStyle = (field?: SortField): React.CSSProperties => ({
    padding: "10px 16px", fontWeight: 700, fontSize: 11.5,
    letterSpacing: "0.04em", textTransform: "uppercase", color: muted,
    borderBottom: `1px solid ${border}`,
    cursor: field ? "pointer" : "default", userSelect: "none",
    whiteSpace: "nowrap", background: subtle,
  });

  const inputStyle: React.CSSProperties = {
    width: "100%", fontFamily: "inherit", fontSize: 13.5,
    padding: "7px 10px", borderRadius: 6,
    border: `1px solid ${inputBorder}`,
    background: inputBg, color: text, boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12, fontWeight: 600, color: muted,
    display: "block", marginBottom: 4,
    textTransform: "uppercase", letterSpacing: "0.04em",
  };

  const coverageOptions: { value: CoverageFilter; label: string; count: number }[] = [
    { value: "all", label: "All", count: rows.length },
    { value: "municipal", label: "Direct license", count: coverageCounts.direct },
    { value: "intermunicipal", label: "Intermunicipal", count: coverageCounts.inter },
    { value: "no_license", label: "No license", count: coverageCounts.none },
    { value: "imbl_eligible", label: "✦ IMBL eligible", count: coverageCounts.imblEligible },
  ];

  const sortOptions: { value: SortField; label: string }[] = [
    { value: "municipality_name", label: "Government name" },
    { value: "region_name", label: "Region" },
    { value: "computed_status", label: "License status" },
    { value: "expiry_date", label: "Expiry date" },
    { value: "cost", label: "Cost (hides unlicensed)" },
  ];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div style={{ fontFamily: "'Source Sans 3', -apple-system, sans-serif", background: bg, minHeight: "100%", color: text }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');
        .lic-row:hover { background: ${darkMode ? "#1F2937" : "#F4F2EC"} !important; }
        .lic-pill { font-family: inherit; font-size: 13px; font-weight: 600; padding: 7px 14px; border-radius: 7px; border: 1px solid ${inputBorder}; background: ${surface}; cursor: pointer; color: ${muted}; transition: all 0.12s ease; }
        .lic-pill:hover { border-color: ${darkMode ? "#6B7280" : "#8A6D3B"}; color: ${text}; }
        .lic-pill.active { background: ${darkMode ? "#3B82F6" : "#2A2820"}; color: #fff; border-color: ${darkMode ? "#3B82F6" : "#2A2820"}; }
        .lic-input { font-family: inherit; border: 1px solid ${inputBorder}; border-radius: 6px; padding: 7px 10px; font-size: 13.5px; background: ${inputBg}; color: ${text}; }
        .lic-input:focus { outline: 2px solid ${darkMode ? "#3B82F6" : "#8A6D3B"}; outline-offset: 1px; }
        .lic-menu-btn { background: none; border: none; cursor: pointer; color: ${muted}; font-size: 18px; padding: 2px 8px; border-radius: 4px; }
        .lic-menu-btn:hover { background: ${subtle}; color: ${text}; }
        .lic-menu { position: absolute; right: 8px; top: 36px; z-index: 50; background: ${surface}; border: 1px solid ${border}; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,${darkMode ? "0.4" : "0.12"}); min-width: 180px; padding: 4px 0; }
        .lic-menu-item { display: block; width: 100%; text-align: left; padding: 8px 14px; font-size: 13px; font-family: inherit; background: none; border: none; cursor: pointer; color: ${text}; }
        .lic-menu-item:hover { background: ${subtle}; }
        .lic-menu-item.danger { color: ${darkMode ? "#F87171" : "#B91C1C"}; }
        .lic-menu-divider { border: none; border-top: 1px solid ${border}; margin: 4px 0; }
        .cov-pill { font-family: inherit; font-size: 12.5px; font-weight: 600; padding: 5px 12px; border-radius: 20px; border: 1px solid ${inputBorder}; background: ${surface}; cursor: pointer; color: ${muted}; transition: all 0.12s ease; white-space: nowrap; }
        .cov-pill:hover { border-color: ${darkMode ? "#6B7280" : "#8A6D3B"}; color: ${text}; }
        .cov-pill.active { background: ${darkMode ? "#1A2540" : "#EAEFFB"}; color: ${darkMode ? "#93C5FD" : "#2C4C9B"}; border-color: ${darkMode ? "#3B82F6" : "#93C5FD"}; }
      `}</style>

      {/* ------------------------------------------------------------------ */}
      {/* Header — title + summary stat row                                   */}
      {/* ------------------------------------------------------------------ */}
      <div style={{ borderBottom: `1px solid ${border}`, padding: "28px 32px 22px", background: bg }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 11.5, letterSpacing: "0.08em", color: accent, fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>
              SCS Group · Regulatory Registry
            </div>
            <h1 style={{ fontFamily: "'Fraunces', serif", fontSize: 30, fontWeight: 600, margin: 0, color: text }}>
              Business License Tracker
            </h1>
            {/* Company switcher — toggles which company's licenses are shown */}
            {companies.length > 0 && (
              <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                <button
                  className={`lic-pill ${activeCompanyId === null ? "active" : ""}`}
                  onClick={() => setActiveCompanyId(null)}
                >
                  All companies
                </button>
                {companies.map(c => (
                  <button
                    key={c.id}
                    className={`lic-pill ${activeCompanyId === c.id ? "active" : ""}`}
                    onClick={() => setActiveCompanyId(c.id)}
                  >
                    {c.short_name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
            <SummaryStat label="Active" value={counts.active} color="#2F9E50" muted={muted} />
            <SummaryStat label="Expiring soon" value={counts.expiringSoon} color="#E2A12E" muted={muted} />
            <SummaryStat label="Expired" value={counts.expired} color="#D14343" muted={muted} />
            <SummaryStat label="No license" value={counts.noLicense} color={darkMode ? "#6B7280" : "#C9BC9C"} muted={muted} />
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Expiry warning banner — dismissable, shows up to 4 names inline     */}
      {/* ------------------------------------------------------------------ */}
      {!dismissedWarning && expiringSoon.length > 0 && (
        <div style={{
          margin: "18px 32px 0",
          background: darkMode ? "#3D2E0A" : "#FCF1DE",
          border: `1px solid ${darkMode ? "#78350F" : "#EBCD8F"}`,
          borderRadius: 10, padding: "13px 18px",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 18 }}>⚠</span>
            <span style={{ fontSize: 13.5, color: darkMode ? "#FBB03B" : "#7A4F0C" }}>
              <strong>{expiringSoon.length}</strong> license{expiringSoon.length === 1 ? "" : "s"} expiring within 30 days:{" "}
              {expiringSoon.slice(0, 4).map(r => r.municipality_name).join(", ")}
              {expiringSoon.length > 4 ? `, +${expiringSoon.length - 4} more` : ""}
            </span>
          </div>
          <button
            onClick={() => setDismissedWarning(true)}
            style={{ background: "none", border: "none", cursor: "pointer", color: darkMode ? "#FBB03B" : "#92600C", fontSize: 13, fontWeight: 600 }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Controls                                                             */}
      {/* Row 1: status pills | search | province | region | sort | actions   */}
      {/* Row 2: coverage + IMBL pills                                         */}
      {/* ------------------------------------------------------------------ */}
      <div style={{ padding: "20px 32px 0", display: "flex", flexDirection: "column", gap: 12 }}>

        {/* Row 1 */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>

          {/* Status filter pills */}
          <div style={{ display: "flex", gap: 6 }}>
            {(["active", "inactive", "all"] as DashboardStatusFilter[]).map(f => (
              <button key={f} className={`lic-pill ${statusFilter === f ? "active" : ""}`} onClick={() => setStatusFilter(f)}>
                {f === "active" ? "Active" : f === "inactive" ? "Inactive" : "All"}
              </button>
            ))}
          </div>

          {/* Municipality search */}
          <input
            className="lic-input"
            placeholder="Search municipality…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ minWidth: 200 }}
          />

          {/* Province filter — clears region when changed */}
          <select
            className="lic-input"
            value={provinceFilter}
            onChange={e => { setProvinceFilter(e.target.value); setRegionFilter(""); }}
            style={{ minWidth: 140 }}
          >
            <option value="">All provinces</option>
            {provinces.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>

          {/* Region filter — scoped to selected province */}
          <select
            className="lic-input"
            value={regionFilter}
            onChange={e => setRegionFilter(e.target.value)}
            style={{ minWidth: 180 }}
          >
            <option value="">All regional districts</option>
            {filteredRegions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>

          {/* Sort by dropdown + direction toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: muted, whiteSpace: "nowrap" }}>Sort by</span>
            <select
              className="lic-input"
              value={sortField}
              onChange={e => setSortField(e.target.value as SortField)}
              style={{ minWidth: 170 }}
            >
              {sortOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button
              className="lic-pill"
              onClick={() => setSortDir(d => d === "asc" ? "desc" : "asc")}
              title={sortDir === "asc" ? "Ascending — click for descending" : "Descending — click for ascending"}
              style={{ padding: "7px 10px", minWidth: 36 }}
            >
              {sortDir === "asc" ? "↑" : "↓"}
            </button>
          </div>

          {/* Show disabled governments toggle */}
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: muted }}>
            <input type="checkbox" checked={showAllTracking} onChange={e => setShowAllTracking(e.target.checked)} />
            Show disabled
          </label>

          {/* Right-side actions: bulk toggles + CSV export */}
          <div style={{ marginLeft: "auto", display: "flex", gap: 8, flexWrap: "wrap" }}>
            {/* Province-level bulk toggle — only when a province is selected and no region */}
            {provinceFilter && !regionFilter && (
              <>
                <button className="lic-pill" onClick={() => handleProvinceBulkToggle(provinceFilter, true)}>Enable all in province</button>
                <button className="lic-pill" onClick={() => handleProvinceBulkToggle(provinceFilter, false)}>Disable all in province</button>
              </>
            )}
            {/* Region-level bulk toggle — only when a specific region is selected */}
            {regionFilter && (
              <>
                <button className="lic-pill" onClick={() => handleRegionBulkToggle(regionFilter, true)}>Enable all in region</button>
                <button className="lic-pill" onClick={() => handleRegionBulkToggle(regionFilter, false)}>Disable all in region</button>
              </>
            )}
            {/* CSV export — exports current filtered + sorted view, including IMBL column */}
            <button className="lic-pill" onClick={() => exportCSV(sortedRows)} title="Export current view as CSV">
              ↓ Export CSV
            </button>
            {/* Add Municipality (renamed from Add Government) */}
            <button className="lic-pill" onClick={() => setAddGovOpen(true)}>
              + Add Municipality
            </button>
          </div>
        </div>

        {/* Row 2: coverage + IMBL filter pills */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: muted, textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 4 }}>
            Coverage:
          </span>
          {coverageOptions.map(opt => (
            <button
              key={opt.value}
              className={`cov-pill ${coverageFilter === opt.value ? "active" : ""}`}
              onClick={() => setCoverageFilter(opt.value)}
            >
              {opt.label}
              <span style={{ marginLeft: 6, fontSize: 11, fontWeight: 700, opacity: 0.7 }}>{opt.count}</span>
            </button>
          ))}
        </div>

      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Main table                                                           */}
      {/* ------------------------------------------------------------------ */}
      <div style={{ padding: "18px 32px 40px" }}>
        {error && (
          <div style={{ padding: 16, background: darkMode ? "#3D1A1A" : "#FBEAEA", color: darkMode ? "#F87171" : "#9B2C2C", borderRadius: 8, marginBottom: 16, fontSize: 13.5 }}>
            {error}
          </div>
        )}

        <div style={{ border: `1px solid ${border}`, borderRadius: 12, overflow: "hidden", background: surface }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5 }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th style={thStyle()}>Province</th>
                <th style={thStyle()}>Region</th>
                <th style={thStyle()}>Government</th>
                <th style={thStyle()}>Tracking</th>
                <th style={thStyle()}>License Status</th>
                <th style={thStyle()}>Expiry Date</th>
                <th style={thStyle()}>Cost</th>
                <th style={{ ...thStyle(), width: 48 }}></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: "center", color: muted }}>Loading…</td></tr>
              ) : sortedRows.length === 0 ? (
                <tr><td colSpan={8} style={{ padding: 32, textAlign: "center", color: muted }}>No governments match these filters.</td></tr>
              ) : (
                sortedRows.map(row => {
                  // Determine IMBL badge to show:
                  // - Blue INTER: already covered by an intermunicipal license
                  // - Yellow IMBL: eligible for IMBL but not yet enrolled
                  // - Nothing: not in any IMBL region
                  const imblRegion = IMBL_LOOKUP[row.municipality_name];
                  const showInterBadge = row.covered_via_region;
                  const showImblBadge = imblRegion && !row.covered_via_region;

                  return (
                    <tr key={row.municipality_id} className="lic-row" style={{ borderBottom: `1px solid ${border}`, background: surface }}>
                      <td style={{ padding: "11px 16px", color: muted }}>{row.province_name}</td>
                      <td style={{ padding: "11px 16px", color: muted }}>{row.region_name}</td>
                      <td style={{ padding: "11px 16px" }}>
                        <div style={{ fontWeight: 600, color: text, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
                          {row.municipality_name}
                          {/* Blue badge: already covered by an intermunicipal license */}
                          {showInterBadge && <InterBadge darkMode={darkMode} />}
                          {/* Yellow badge: eligible for IMBL but not yet enrolled */}
                          {showImblBadge && <ImblEligibleBadge regionName={imblRegion} darkMode={darkMode} />}
                        </div>
                        <div style={{ fontSize: 11.5, color: accent }}>{row.municipality_type}</div>
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        {/* Inline confirm popover — click to toggle tracking */}
                        <TrackingCell row={row} darkMode={darkMode} onToggle={handleTrackingToggle} />
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        {/* Inline status dropdown — click badge to override status */}
                        <StatusCell row={row} darkMode={darkMode} onStatusChange={handleStatusChange} />
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        {row.expiry_date ? (
                          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.3 }}>
                            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: text }}>
                              {row.expiry_date}
                            </span>
                            {(row.computed_status === "Expiring Soon" || row.computed_status === "Expired") && (
                              <span style={{ fontSize: 11.5, fontWeight: 600, color: row.computed_status === "Expired" ? "#D14343" : "#E2A12E" }}>
                                {row.computed_status === "Expired"
                                  ? `Expired ${Math.abs(row.days_until_expiry ?? 0)}d ago`
                                  : `${row.days_until_expiry}d remaining`}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span style={{ color: darkMode ? "#4B5563" : "#A6A092" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "11px 16px" }}>
                        {row.cost != null ? (
                          <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: text }}>
                            ${Number(row.cost).toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        ) : (
                          <span style={{ color: darkMode ? "#4B5563" : "#A6A092" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "11px 8px", position: "relative" }}>
                        <button
                          className="lic-menu-btn"
                          onClick={() => setMenuOpenId(menuOpenId === row.municipality_id ? null : row.municipality_id)}
                        >
                          ···
                        </button>
                        {menuOpenId === row.municipality_id && (
                          <>
                            <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setMenuOpenId(null)} />
                            <div className="lic-menu">
                              <button className="lic-menu-item" onClick={() => openEdit(row)}>
                                {row.license_id ? "✏️ Edit license" : "＋ Add license"}
                              </button>
                              {row.license_id && (
                                <>
                                  <hr className="lic-menu-divider" />
                                  <button className="lic-menu-item danger" onClick={() => handleDeleteLicense(row)}>
                                    🗑 Remove license
                                  </button>
                                </>
                              )}
                            </div>
                          </>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Row count footer */}
        <div style={{ marginTop: 10, fontSize: 12.5, color: muted, textAlign: "right" }}>
          Showing {sortedRows.length} of {rows.length} governments
          {sortField === "cost" && (
            <span style={{ marginLeft: 8, color: darkMode ? "#FBB03B" : "#92600C" }}>
              · unlicensed municipalities hidden (cost sort active)
            </span>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* License add / edit modal                                             */}
      {/* ------------------------------------------------------------------ */}
      {editingRow && (
        <>
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100 }} onClick={() => setEditingRow(null)} />
          <div style={{
            position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
            zIndex: 101, background: surface, border: `1px solid ${border}`,
            borderRadius: 14, padding: 28, width: 480, maxWidth: "95vw",
            boxShadow: "0 8px 40px rgba(0,0,0,0.3)", maxHeight: "90vh", overflowY: "auto",
          }}>
            <h2 style={{ fontFamily: "'Fraunces', serif", fontSize: 20, fontWeight: 600, margin: "0 0 4px", color: text }}>
              {editingRow.license_id ? "Edit License" : "Add License"}
            </h2>
            <p style={{ fontSize: 13, color: muted, margin: "0 0 4px" }}>
              {editingRow.municipality_name} · {editingRow.region_name}
            </p>
            {/* Show IMBL eligibility hint in the modal if applicable */}
            {IMBL_LOOKUP[editingRow.municipality_name] && !editingRow.covered_via_region && (
              <p style={{ fontSize: 12.5, color: darkMode ? "#FBB03B" : "#92600C", margin: "0 0 16px" }}>
                ✦ This municipality is eligible for the <strong>{IMBL_LOOKUP[editingRow.municipality_name]}</strong> IMBL.
                Consider adding an Intermunicipal-scope license to cover the whole region at once.
              </p>
            )}

            {formError && (
              <div style={{ padding: "8px 12px", background: darkMode ? "#3D1A1A" : "#FBEAEA", color: darkMode ? "#F87171" : "#9B2C2C", borderRadius: 6, marginBottom: 16, fontSize: 13 }}>
                {formError}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Scope</label>
                <select style={inputStyle} value={form.scope} onChange={e => setForm(f => ({ ...f, scope: e.target.value as "Municipal" | "Intermunicipal" }))}>
                  <option value="Municipal">Municipal (this city only)</option>
                  <option value="Intermunicipal">Intermunicipal (entire region)</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>License Number</label>
                <input style={inputStyle} value={form.license_number} onChange={e => setForm(f => ({ ...f, license_number: e.target.value }))} placeholder="e.g. SUR-2026-001" />
              </div>
              <div>
                <label style={labelStyle}>Issuing Authority</label>
                <input style={inputStyle} value={form.issuing_authority} onChange={e => setForm(f => ({ ...f, issuing_authority: e.target.value }))} placeholder="e.g. City of Surrey" />
              </div>
              <div>
                <label style={labelStyle}>Issue Date</label>
                <input style={inputStyle} type="date" value={form.issue_date} onChange={e => setForm(f => ({ ...f, issue_date: e.target.value }))} />
              </div>
              <div>
                <label style={labelStyle}>Expiry Date *</label>
                <input style={inputStyle} type="date" value={form.expiry_date} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} />
              </div>
              <div>
                <label style={labelStyle}>Cost ($)</label>
                <input style={inputStyle} type="number" value={form.cost} onChange={e => setForm(f => ({ ...f, cost: e.target.value }))} placeholder="0.00" />
              </div>
              <div>
                <label style={labelStyle}>Status Override</label>
                <select style={inputStyle} value={form.status_override} onChange={e => setForm(f => ({ ...f, status_override: e.target.value as LicenseStatus | "" }))}>
                  <option value="">Auto (from expiry date)</option>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                  <option value="Pending">Pending</option>
                  <option value="Expired">Expired</option>
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Notes</label>
                <textarea
                  style={{ ...inputStyle, resize: "vertical", minHeight: 64 }}
                  value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                  placeholder="Optional notes…"
                />
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Applies to</label>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  {companies.map(c => (
                    <label
                      key={c.id}
                      style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13.5, color: text, cursor: "pointer" }}
                    >
                      <input
                        type="checkbox"
                        checked={form.company_ids.includes(c.id)}
                        onChange={e => setForm(f => ({
                          ...f,
                          company_ids: e.target.checked
                            ? [...f.company_ids, c.id]
                            : f.company_ids.filter(id => id !== c.id),
                        }))}
                      />
                      {c.name}
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
              <button className="lic-pill" onClick={() => setEditingRow(null)}>Cancel</button>
              <button
                className="lic-pill active"
                onClick={handleFormSave}
                disabled={formLoading}
                style={{ opacity: formLoading ? 0.6 : 1 }}
              >
                {formLoading ? "Saving…" : "Save License"}
              </button>
            </div>
          </div>
        </>
      )}
      {addGovOpen && (
        <AddGovernmentModal
          darkMode={darkMode}
          provinces={provinces}
          regions={regions}
          companies={companies}
          onClose={() => setAddGovOpen(false)}
          onDone={() => { setAddGovOpen(false); loadAll(); }}
        />
      )}
    </div>
  );
}
// ---------------------------------------------------------------------------
// SummaryStat — one of the four header counters (Active / Expiring / etc.)
// ---------------------------------------------------------------------------
function SummaryStat({ label, value, color, muted }: { label: string; value: number; color: string; muted: string }) {
  return (
    <div style={{ textAlign: "right" }}>
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 22, fontWeight: 600, color }}>{value}</div>
      <div style={{ fontSize: 11, color: muted, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
    </div>
  );
}
// ---------------------------------------------------------------------------
// Add Government Modal
// Lets users add a municipality that isn't in the seeded list —
// e.g. a different province, or a newly incorporated municipality.
// Province and regional district can be selected from existing ones
// or created on the fly by typing a new name.
// Optionally add a license in the same flow.
// ---------------------------------------------------------------------------
function AddGovernmentModal({
  darkMode,
  provinces,
  regions,
  companies,
  onClose,
  onDone,
}: {
  darkMode: boolean;
  provinces: Province[];
  regions: RegionalDistrict[];
  companies: Company[];
  onClose: () => void;
  onDone: () => void;
}) {
  const surface = darkMode ? "#1F2937" : "#FFFFFF";
  const border = darkMode ? "#374151" : "#E4DFD0";
  const text = darkMode ? "#F9FAFB" : "#2A2820";
  const muted = darkMode ? "#9CA3AF" : "#7A7460";
  const subtle = darkMode ? "#374151" : "#F4F2EC";
  const inputBg = darkMode ? "#374151" : "#FFFFFF";
  const inputBorder = darkMode ? "#4B5563" : "#DBD6C8";

  const inputStyle: React.CSSProperties = {
    width: "100%", fontFamily: "inherit", fontSize: 13.5,
    padding: "7px 10px", borderRadius: 6,
    border: `1px solid ${inputBorder}`,
    background: inputBg, color: text, boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12, fontWeight: 600, color: muted,
    display: "block", marginBottom: 4,
    textTransform: "uppercase", letterSpacing: "0.04em",
  };

  // --- Location fields ---
  const [provinceMode, setProvinceMode] = useState<"existing" | "new">("existing");
  const [selectedProvinceId, setSelectedProvinceId] = useState<string>("");
  const [newProvinceName, setNewProvinceName] = useState("");
  const [newProvinceCode, setNewProvinceCode] = useState("");

  const [regionMode, setRegionMode] = useState<"existing" | "new">("existing");
  const [selectedRegionId, setSelectedRegionId] = useState<string>("");
  const [newRegionName, setNewRegionName] = useState("");

  const [municipalityName, setMunicipalityName] = useState("");
  const [municipalityType, setMunicipalityType] = useState("City");

  // --- Optional license fields ---
  const [addLicense, setAddLicense] = useState(false);
  const [licenseNumber, setLicenseNumber] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [cost, setCost] = useState("");
  const [scope, setScope] = useState<"Municipal" | "Intermunicipal">("Municipal");
  const [statusOverride, setStatusOverride] = useState<LicenseStatus | "">("");
  const [licenseCompanyIds, setLicenseCompanyIds] = useState<string[]>([]);
  const [notes, setNotes] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter regions to selected province
  const availableRegions = useMemo(() => {
    if (!selectedProvinceId) return regions;
    return regions.filter(r => r.province_id === selectedProvinceId);
  }, [regions, selectedProvinceId]);

  const municipalityTypes = [
    "City", "District Municipality", "Town", "Village",
    "Island Municipality", "Mountain Resort Municipality",
    "Resort Municipality", "Indian Government District", "Other",
  ];

  const handleSave = async () => {
    // Validate required fields
    if (!municipalityName.trim()) { setError("Municipality name is required."); return; }
    if (provinceMode === "existing" && !selectedProvinceId) { setError("Please select a province."); return; }
    if (provinceMode === "new" && (!newProvinceName.trim() || !newProvinceCode.trim())) { setError("New province requires a name and 2-letter code."); return; }
    if (regionMode === "existing" && !selectedRegionId) { setError("Please select a regional district."); return; }
    if (regionMode === "new" && !newRegionName.trim()) { setError("New regional district requires a name."); return; }
    if (addLicense && !expiryDate) { setError("Expiry date is required when adding a license."); return; }

    setSaving(true);
    setError(null);

    try {
      // Step 1: Resolve or create province
      let provinceId = selectedProvinceId;
      if (provinceMode === "new") {
        const res = await fetch("/api/licensing/provinces", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ name: newProvinceName.trim(), code: newProvinceCode.trim().toUpperCase() }),
        });
        if (!res.ok) throw new Error("Failed to create province");
        const created = await res.json();
        provinceId = created.id;
      }

      // Step 2: Resolve or create regional district
      let regionId = selectedRegionId;
      if (regionMode === "new") {
        const res = await fetch("/api/licensing/regional-districts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ name: newRegionName.trim(), province_id: provinceId }),
        });
        if (!res.ok) throw new Error("Failed to create regional district");
        const created = await res.json();
        regionId = created.id;
      }

      // Step 3: Create municipality
      const muni = await createMunicipality({
        name: municipalityName.trim(),
        municipality_type: municipalityType as any,
        regional_district_id: regionId,
        tracking_enabled: true,
      });

      // Step 4: Optionally create license
      if (addLicense && expiryDate) {
        const payload: CreateLicensePayload = {
          scope,
          expiry_date: expiryDate,
          license_number: licenseNumber || undefined,
          issue_date: issueDate || undefined,
          cost: cost ? parseFloat(cost) : undefined,
          status_override: (statusOverride as LicenseStatus) || undefined,
          notes: notes || undefined,
        };
        if (scope === "Municipal") {
          payload.municipality_id = muni.id;
        } else {
          payload.regional_district_id = regionId;
        }
        const createdLicense = await createLicense(payload);

        // Assign companies
        if (licenseCompanyIds.length > 0) {
          await Promise.all(licenseCompanyIds.map(id => addCompanyToLicense(createdLicense.id, id)));
        }
      }

      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100 }} onClick={onClose} />
      <div style={{
        position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)",
        zIndex: 101, background: surface, border: `1px solid ${border}`,
        borderRadius: 14, padding: 28, width: 540, maxWidth: "95vw",
        boxShadow: "0 8px 40px rgba(0,0,0,0.3)", maxHeight: "90vh", overflowY: "auto",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontFamily: "'Fraunces', serif", fontSize: 20, fontWeight: 600, margin: "0 0 4px", color: text }}>
              Add Government
            </h2>
            <p style={{ fontSize: 12.5, color: muted, margin: 0 }}>
              Add a municipality that isn't in the system yet
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: muted, fontSize: 20, lineHeight: 1 }}>✕</button>
        </div>

        {error && (
          <div style={{ padding: "8px 12px", background: darkMode ? "#3D1A1A" : "#FBEAEA", color: darkMode ? "#F87171" : "#9B2C2C", borderRadius: 6, marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* ---- Location section ---- */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: muted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 12, paddingBottom: 6, borderBottom: `1px solid ${border}` }}>
            Location
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>

            {/* Province */}
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Province</label>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <button
                  onClick={() => setProvinceMode("existing")}
                  style={{ fontSize: 12.5, padding: "4px 12px", borderRadius: 6, border: `1px solid ${inputBorder}`, background: provinceMode === "existing" ? (darkMode ? "#3B82F6" : "#2A2820") : "none", color: provinceMode === "existing" ? "#fff" : muted, cursor: "pointer", fontFamily: "inherit" }}
                >
                  Existing
                </button>
                <button
                  onClick={() => setProvinceMode("new")}
                  style={{ fontSize: 12.5, padding: "4px 12px", borderRadius: 6, border: `1px solid ${inputBorder}`, background: provinceMode === "new" ? (darkMode ? "#3B82F6" : "#2A2820") : "none", color: provinceMode === "new" ? "#fff" : muted, cursor: "pointer", fontFamily: "inherit" }}
                >
                  + New province
                </button>
              </div>
              {provinceMode === "existing" ? (
                <select style={inputStyle} value={selectedProvinceId} onChange={e => { setSelectedProvinceId(e.target.value); setSelectedRegionId(""); }}>
                  <option value="">Select province…</option>
                  {provinces.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
                  <input style={inputStyle} placeholder="Province name (e.g. Alberta)" value={newProvinceName} onChange={e => setNewProvinceName(e.target.value)} />
                  <input style={{ ...inputStyle, width: 60 }} placeholder="AB" maxLength={2} value={newProvinceCode} onChange={e => setNewProvinceCode(e.target.value)} />
                </div>
              )}
            </div>

            {/* Regional District */}
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>Regional District</label>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <button
                  onClick={() => setRegionMode("existing")}
                  style={{ fontSize: 12.5, padding: "4px 12px", borderRadius: 6, border: `1px solid ${inputBorder}`, background: regionMode === "existing" ? (darkMode ? "#3B82F6" : "#2A2820") : "none", color: regionMode === "existing" ? "#fff" : muted, cursor: "pointer", fontFamily: "inherit" }}
                >
                  Existing
                </button>
                <button
                  onClick={() => setRegionMode("new")}
                  style={{ fontSize: 12.5, padding: "4px 12px", borderRadius: 6, border: `1px solid ${inputBorder}`, background: regionMode === "new" ? (darkMode ? "#3B82F6" : "#2A2820") : "none", color: regionMode === "new" ? "#fff" : muted, cursor: "pointer", fontFamily: "inherit" }}
                >
                  + New region
                </button>
              </div>
              {regionMode === "existing" ? (
                <select style={inputStyle} value={selectedRegionId} onChange={e => setSelectedRegionId(e.target.value)}>
                  <option value="">Select regional district…</option>
                  {availableRegions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              ) : (
                <input style={inputStyle} placeholder="Regional district name" value={newRegionName} onChange={e => setNewRegionName(e.target.value)} />
              )}
            </div>

            {/* Municipality name */}
            <div>
              <label style={labelStyle}>Municipality Name *</label>
              <input style={inputStyle} placeholder="e.g. Red Deer" value={municipalityName} onChange={e => setMunicipalityName(e.target.value)} />
            </div>

            {/* Municipality type */}
            <div>
              <label style={labelStyle}>Type</label>
              <select style={inputStyle} value={municipalityType} onChange={e => setMunicipalityType(e.target.value)}>
                {municipalityTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

          </div>
        </div>

        {/* ---- Optional license section ---- */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", marginBottom: addLicense ? 12 : 0 }}>
            <input type="checkbox" checked={addLicense} onChange={e => setAddLicense(e.target.checked)} />
            <span style={{ fontSize: 13, fontWeight: 600, color: text }}>Also add a license now</span>
          </label>

          {addLicense && (
            <div style={{ paddingTop: 12, borderTop: `1px solid ${border}` }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div style={{ gridColumn: "1 / -1" }}>
                  <label style={labelStyle}>Scope</label>
                  <select style={inputStyle} value={scope} onChange={e => setScope(e.target.value as "Municipal" | "Intermunicipal")}>
                    <option value="Municipal">Municipal (this city only)</option>
                    <option value="Intermunicipal">Intermunicipal (entire region)</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>License Number</label>
                  <input style={inputStyle} placeholder="e.g. RED-2026-001" value={licenseNumber} onChange={e => setLicenseNumber(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Issuing Authority</label>
                  <input style={inputStyle} placeholder="e.g. City of Red Deer" value={notes} onChange={e => setNotes(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Issue Date</label>
                  <input style={inputStyle} type="date" value={issueDate} onChange={e => setIssueDate(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Expiry Date *</label>
                  <input style={inputStyle} type="date" value={expiryDate} onChange={e => setExpiryDate(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Cost ($)</label>
                  <input style={inputStyle} type="number" placeholder="0.00" value={cost} onChange={e => setCost(e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Status Override</label>
                  <select style={inputStyle} value={statusOverride} onChange={e => setStatusOverride(e.target.value as LicenseStatus | "")}>
                    <option value="">Auto (from expiry date)</option>
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                    <option value="Pending">Pending</option>
                    <option value="Expired">Expired</option>
                  </select>
                </div>
                {companies.length > 0 && (
                  <div style={{ gridColumn: "1 / -1" }}>
                    <label style={labelStyle}>Applies to</label>
                    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                      {companies.map(c => (
                        <label key={c.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13.5, color: text, cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={licenseCompanyIds.includes(c.id)}
                            onChange={e => setLicenseCompanyIds(prev =>
                              e.target.checked ? [...prev, c.id] : prev.filter(id => id !== c.id)
                            )}
                          />
                          {c.name}
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ---- Actions ---- */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button
            onClick={onClose}
            style={{ fontSize: 13, padding: "7px 16px", borderRadius: 7, border: `1px solid ${inputBorder}`, background: "none", cursor: "pointer", color: text, fontFamily: "inherit" }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              fontSize: 13, padding: "7px 20px", borderRadius: 7, border: "none",
              background: darkMode ? "#3B82F6" : "#2A2820",
              color: "#fff", fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.6 : 1, fontFamily: "inherit",
            }}
          >
            {saving ? "Saving…" : addLicense ? "Add Government & License" : "Add Government"}
          </button>
        </div>
      </div>
    </>
  );
}