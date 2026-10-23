import { useEffect, useMemo, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Copy, Sparkles } from "lucide-react";

// Adjust to your real API client (lib/api.ts / lib/dms.ts)
import { apiFetch } from "@/lib/api";

type FieldStatus = "pending" | "accepted" | "corrected" | "rejected";

interface FieldRow {
  field_name: string;
  value: unknown;
  originalValue: unknown;
  confidence: number | null;
  low_confidence: boolean;
  status: FieldStatus;
  draftValue: string;
}

interface DocumentDetail {
  document_version_id: string;
  status: string;
  fields: {
    field_name: string;
    value: unknown;
    confidence: number | null;
    low_confidence: boolean;
  }[];
  document_types: string[];
  document_data: Record<string, unknown>;
}

function displayValue(value: unknown): string {
  if (value == null) return "";
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function dateInputValue(value: string): string {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "" : parsed.toISOString().slice(0, 10);
}

// Groups fields for display only - purely a client-side label mapping,
// no backend concept of "sections". Add field names here as your
// TARGET_FIELDS list in doctr_engine.py grows.
const FIELD_GROUPS: { label: string; fields: string[] }[] = [
  { label: "Header", fields: ["document_type", "invoice_number", "document_date", "due_date", "payment_terms"] },
  { label: "Vendor", fields: ["vendor", "bill_to", "gst_number", "pst_number"] },
  { label: "Totals", fields: ["grand_total", "account_number"] },
];

function fieldLabel(name: string): string {
  return name
    .split("_")
    .map((w) => w[0]?.toUpperCase() + w.slice(1))
    .join(" ");
}

function confidenceColor(confidence: number | null): string {
  if (confidence === null) return "text-red-400";
  if (confidence >= 0.90) return "text-emerald-400";
  if (confidence >= 0.75) return "text-amber-400";
  return "text-red-400";
}

function confidenceBarColor(confidence: number | null): string {
  if (confidence === null) return "bg-red-400";
  if (confidence >= 0.90) return "bg-emerald-400";
  if (confidence >= 0.75) return "bg-amber-400";
  return "bg-red-400";
}

export default function CorrectionReview({
  documentVersionId,
  filename,
  documentTypeLabel,
  onSubmitted,
  onPrev,
  onNext,
  onBack,
  position,
}: {
  documentVersionId: string;
  filename: string;
  documentTypeLabel?: string;
  onSubmitted?: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onBack?: () => void;
  position?: { index: number; total: number };
}) {
  const [rows, setRows] = useState<FieldRow[]>([]);
  const [documentTypes, setDocumentTypes] = useState<string[]>([]);
  const [storedDocumentData, setStoredDocumentData] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [rightTab, setRightTab] = useState<"json" | "summary" | "database">("json");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch<DocumentDetail>(`/correction-queue/${documentVersionId}`)
      .then((detail) => {
        if (cancelled) return;
        setRows(
          detail.fields.map((f) => ({
            ...f,
            originalValue: f.value,
            status: "pending",
            draftValue: displayValue(f.value),
          }))
        );
        setDocumentTypes(detail.document_types);
        setStoredDocumentData(detail.document_data);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [documentVersionId]);

  const resolvedCount = rows.filter((r) => r.status !== "pending").length;
  const correctedCount = rows.filter((r) => r.status === "corrected").length;
  const rejectedCount = rows.filter((r) => r.status === "rejected").length;
  const lowConfidencePendingCount = rows.filter((r) => r.low_confidence && r.status === "pending").length;
  const percentComplete = rows.length ? Math.round((resolvedCount / rows.length) * 100) : 0;
  const canSubmit = rows.length > 0 && resolvedCount === rows.length;

  const jsonPreview = useMemo(() => {
    const obj: Record<string, unknown> = {};
    for (const r of rows) {
      if (r.status === "rejected") {
        obj[r.field_name] = null;
      } else if (r.status !== "corrected") {
        obj[r.field_name] = r.originalValue;
      } else if (r.originalValue !== null && typeof r.originalValue === "object") {
        try {
          obj[r.field_name] = JSON.parse(r.draftValue);
        } catch {
          obj[r.field_name] = r.draftValue;
        }
      } else {
        obj[r.field_name] = r.draftValue;
      }
    }
    return obj;
  }, [rows]);

  function updateRow(fieldName: string, patch: Partial<FieldRow>) {
    setRows((prev) => prev.map((r) => (r.field_name === fieldName ? { ...r, ...patch } : r)));
  }

  function acceptField(fieldName: string) {
    updateRow(fieldName, { status: "accepted" });
  }

  function editField(fieldName: string, value: string) {
    updateRow(fieldName, { draftValue: value, status: "corrected" });
  }

  function acceptAll() {
    // Deliberately skips low-confidence fields still pending - those
    // need individual review, matching the zero-tolerance requirement.
    // Accept All is a convenience for the already-confident majority,
    // not a way to bulk-dismiss flagged fields.
    setRows((prev) =>
      prev.map((r) =>
        r.status === "pending" && !r.low_confidence ? { ...r, status: "accepted" } : r
      )
    );
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const fields = rows.map((r) => {
        let value: unknown = r.draftValue;
        if (r.originalValue !== null && typeof r.originalValue === "object" && r.status === "corrected") {
          try {
            value = JSON.parse(r.draftValue);
          } catch {
            throw new Error(`${fieldLabel(r.field_name)} must contain valid JSON`);
          }
        }
        return {
          field_name: r.field_name,
          value_corrected: r.status === "rejected" ? null : value,
          action: r.status === "pending" ? "accepted" : r.status,
        };
      });
      await apiFetch(`/correction-queue/${documentVersionId}/submit`, {
        method: "POST",
        body: JSON.stringify({ fields }),
      });
      onSubmitted?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  const rowsByGroup = FIELD_GROUPS.map((group) => ({
    ...group,
    rows: rows.filter((r) => group.fields.includes(r.field_name)),
  })).filter((g) => g.rows.length > 0);

  const ungrouped = rows.filter(
    (r) => !FIELD_GROUPS.some((g) => g.fields.includes(r.field_name))
  );

  if (loading) {
    return <div className="p-8 text-sm text-slate-400">Loading document…</div>;
  }

  return (
    <div className="flex h-full flex-col bg-[#0b0f1a] text-slate-200">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2 text-sm">
          <button onClick={onBack} className="text-slate-400 hover:text-slate-200">
            <ChevronLeft className="inline h-4 w-4" /> Documents
          </button>
          <Sparkles className="h-4 w-4 text-indigo-400" />
          <span className="font-medium text-slate-100">{filename}</span>
          {documentTypeLabel && (
            <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-xs text-indigo-300">
              {documentTypeLabel}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
      <button
            onClick={onPrev}
            disabled={!onPrev}
            className="text-slate-500 hover:text-slate-300 disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-slate-500">
            {position ? `${position.index + 1} / ${position.total}` : ""}
          </span>
          <button
            onClick={onNext}
            disabled={!onNext}
            className="text-slate-500 hover:text-slate-300 disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <button
            onClick={acceptAll}
            className="rounded bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
          >
            Accept All
          </button>
          <button
            onClick={submit}
            disabled={!canSubmit || submitting}
            className="flex items-center gap-1.5 rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Submit Corrections
          </button>
        </div>
      </div>

      {/* Status strip */}
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2 text-xs text-slate-400">
        <span>
          {resolvedCount} of {rows.length} fields resolved · {correctedCount} corrected · {rejectedCount} rejected
        </span>
        <span className="font-medium text-indigo-300">{percentComplete}% complete</span>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Fields column */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {rowsByGroup.map((group) => (
                <FieldGroup
              key={group.label}
              label={group.label}
              rows={group.rows}
                  documentTypes={documentTypes}
              onAccept={acceptField}
              onEdit={editField}
            />
          ))}
          {ungrouped.length > 0 && (
            <FieldGroup label="Other" rows={ungrouped} documentTypes={documentTypes} onAccept={acceptField} onEdit={editField} />
          )}
        </div>

        {/* JSON / Summary panel */}
        <div className="w-96 border-l border-slate-800 px-4 py-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex gap-1 rounded bg-slate-900 p-0.5 text-xs">
              <button
                onClick={() => setRightTab("json")}
                className={`rounded px-2 py-1 ${rightTab === "json" ? "bg-slate-700 text-slate-100" : "text-slate-400"}`}
              >
                {"</>"} JSON
              </button>
              <button
                onClick={() => setRightTab("database")}
                className={`rounded px-2 py-1 ${rightTab === "database" ? "bg-slate-700 text-slate-100" : "text-slate-400"}`}
              >
                Stored
              </button>
              <button
                onClick={() => setRightTab("summary")}
                className={`rounded px-2 py-1 ${rightTab === "summary" ? "bg-slate-700 text-slate-100" : "text-slate-400"}`}
              >
                Summary
              </button>
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(JSON.stringify(rightTab === "database" ? storedDocumentData : jsonPreview, null, 2))}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
            >
              <Copy className="h-3.5 w-3.5" /> Copy
            </button>
          </div>

          {rightTab === "database" ? (
            <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-300">
              {JSON.stringify(storedDocumentData, null, 2)}
            </pre>
          ) : Object.keys(jsonPreview).length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-center text-xs text-slate-500">
              <div className="mb-2 text-2xl">📄</div>
              No extracted JSON fields are stored for this version
            </div>
          ) : rightTab === "json" ? (
            <pre className="whitespace-pre-wrap break-words font-mono text-xs text-slate-300">
              {JSON.stringify(jsonPreview, null, 2)}
            </pre>
          ) : (
            <ul className="space-y-1 text-xs text-slate-300">
              {Object.entries(jsonPreview).map(([k, v]) => (
                <li key={k}>
                  <span className="text-slate-500">{fieldLabel(k)}:</span> {v == null ? "—" : displayValue(v)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Bottom warning */}
      {lowConfidencePendingCount > 0 && (
        <div className="border-t border-amber-900/50 bg-amber-950/30 px-4 py-2 text-xs text-amber-300">
          ⚠ {lowConfidencePendingCount} low-confidence field{lowConfidencePendingCount === 1 ? "" : "s"} need review before submitting
        </div>
      )}
      {error && (
        <div className="border-t border-red-900/50 bg-red-950/30 px-4 py-2 text-xs text-red-300">{error}</div>
      )}
    </div>
  );
}

function FieldGroup({
  label,
  rows,
  documentTypes,
  onAccept,
  onEdit,
}: {
  label: string;
  rows: FieldRow[];
  documentTypes: string[];
  onAccept: (fieldName: string) => void;
  onEdit: (fieldName: string, value: string) => void;
}) {
  const resolved = rows.filter((r) => r.status !== "pending").length;
  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
        <span>{label}</span>
        <span>
          {resolved}/{rows.length}
        </span>
      </div>
      <div className="space-y-2">
        {rows.map((row) => (
              <FieldCard key={row.field_name} row={row} documentTypes={documentTypes} onAccept={onAccept} onEdit={onEdit} />
        ))}
      </div>
    </div>
  );
}

function FieldCard({
  row,
  documentTypes,
  onAccept,
  onEdit,
}: {
  row: FieldRow;
  documentTypes: string[];
  onAccept: (fieldName: string) => void;
  onEdit: (fieldName: string, value: string) => void;
}) {
  const barColor = confidenceBarColor(row.confidence);
  const textColor = confidenceColor(row.confidence);
  const statusLabel =
    row.status === "pending" ? "Pending" : row.status === "accepted" ? "Accepted" : row.status === "corrected" ? "Corrected" : "Rejected";
  const statusColor =
    row.status === "pending"
      ? "bg-slate-800 text-slate-400"
      : row.status === "rejected"
      ? "bg-red-900/40 text-red-300"
      : "bg-emerald-900/40 text-emerald-300";

  return (
    <div className={`relative rounded-lg border border-slate-800 bg-slate-900/60 py-3 pl-4 pr-3`}>
      <span className={`absolute left-0 top-0 h-full w-1 rounded-l-lg ${barColor}`} />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {row.confidence !== null && (
            <span className={`font-mono ${textColor}`}>{Math.round(row.confidence * 100)}%</span>
          )}
          <span>{fieldLabel(row.field_name)}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-[10px] font-medium ${statusColor}`}>{statusLabel}</span>
          {row.status !== "accepted" && (
            <button
              onClick={() => onAccept(row.field_name)}
              title="Accept as-is"
              className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-emerald-400"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
      {row.field_name === "document_type" ? (
        <select
          value={row.draftValue}
          onChange={(e) => onEdit(row.field_name, e.target.value)}
          className="mt-1 w-full rounded bg-slate-800 px-2 py-1 font-mono text-sm text-slate-100"
        >
          <option value="">No document type</option>
          {documentTypes.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
      ) : row.field_name === "due_date" ? (
        <input
          type="date"
          value={dateInputValue(row.draftValue)}
          onChange={(e) => onEdit(row.field_name, e.target.value)}
          className="mt-1 w-full rounded bg-slate-800 px-2 py-1 font-mono text-sm text-slate-100"
        />
      ) : row.originalValue !== null && typeof row.originalValue === "object" ? (
        <textarea
          value={row.draftValue}
          onChange={(e) => onEdit(row.field_name, e.target.value)}
          rows={4}
          className="mt-1 w-full rounded bg-slate-800 px-2 py-1 font-mono text-xs text-slate-100"
        />
      ) : (
        <input
          value={row.draftValue}
          onChange={(e) => onEdit(row.field_name, e.target.value)}
          className="mt-1 w-full bg-transparent font-mono text-sm text-slate-100 outline-none focus:text-white"
        />
      )}
    </div>
  );
}
