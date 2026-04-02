import { CalendarClock } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";

export type DuePayment = {
  documentId: string;
  versionId: string;
  filename: string;
  dueDate: string;
};

interface UpcomingDuePaymentsPanelProps {
  items: DuePayment[];
  loading?: boolean;
  darkMode?: boolean;
  onPreview?: (item: DuePayment) => void;
  daysAhead: number;
  onDaysAheadChange: (days: number) => void;
  hasAccess: boolean;
}

function parseDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function formatDate(value: string): string {
  const date = parseDate(value);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(date);
}

function formatCountdown(value: string): string {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const due = parseDate(value);
  const diffMs = due.getTime() - start.getTime();
  const days = Math.max(0, Math.round(diffMs / (1000 * 60 * 60 * 24)));
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}

export function UpcomingDuePaymentsPanel({
  items,
  loading,
  darkMode,
  onPreview,
  daysAhead,
  onDaysAheadChange,
  hasAccess,
}: UpcomingDuePaymentsPanelProps) {
  const options = [
    { label: "1 week", value: 7 },
    { label: "2 weeks", value: 14 },
    { label: "30 days", value: 30 },
    { label: "45 days", value: 45 },
    { label: "60 days", value: 60 },
  ];
  return (
    <aside
      className={`rounded-2xl border p-5 shadow-sm ${
        darkMode ? "border-gray-700 bg-gray-900/60 text-gray-100" : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`flex h-9 w-9 items-center justify-center rounded-full ${
            darkMode ? "bg-blue-900/40 text-blue-200" : "bg-blue-50 text-blue-700"
          }`}>
            <CalendarClock className="h-4 w-4" />
          </div>
          <div>
            <div className="text-lg font-semibold">Upcoming Payments</div>
            <div className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
              Incoming invoice due dates
            </div>
          </div>
        </div>

        <div className="min-w-[140px]">
          <Select
            value={String(daysAhead)}
            onValueChange={(value) => onDaysAheadChange(Number(value))}
            disabled={!hasAccess}
          >
            <SelectTrigger className={darkMode ? "bg-gray-800 border-gray-700 text-gray-100" : ""}>
              <SelectValue placeholder="Window" />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem
                  key={option.value}
                  value={String(option.value)}
                  className={darkMode ? "text-gray-200 focus:bg-gray-700" : ""}
                >
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {!hasAccess && (
          <div className={`rounded-lg border px-3 py-3 text-sm ${
            darkMode ? "border-gray-700 text-gray-300" : "border-gray-200 text-gray-600"
          }`}>
            You do not have access to upcoming payments. Ask an admin to grant
            <span className="font-semibold"> document.due_payments</span>.
          </div>
        )}

        {hasAccess && loading && (
          <div className={`rounded-lg border px-3 py-3 text-sm ${
            darkMode ? "border-gray-700 text-gray-400" : "border-gray-200 text-gray-500"
          }`}>
            Loading upcoming due dates...
          </div>
        )}

        {hasAccess && !loading && items.length === 0 && (
          <div className={`rounded-lg border px-3 py-3 text-sm ${
            darkMode ? "border-gray-700 text-gray-400" : "border-gray-200 text-gray-500"
          }`}>
            No upcoming payments in the selected window.
          </div>
        )}

        {hasAccess && !loading &&
          items.map((item) => {
            const clickable = Boolean(onPreview);
            return (
              <button
                key={`${item.documentId}-${item.versionId}`}
                type="button"
                onClick={() => onPreview?.(item)}
                className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                  darkMode ? "border-gray-700 bg-gray-900/40 hover:border-blue-500/60 hover:bg-gray-900/70" : "border-gray-200 bg-gray-50 hover:border-blue-200 hover:bg-white"
                } ${clickable ? "cursor-pointer" : "cursor-default"}`}
                disabled={!clickable}
              >
                <div className={`text-sm font-medium ${
                  darkMode ? "text-gray-100" : "text-gray-800"
                }`}>
                  {item.filename}
                </div>
                <div className="mt-1 flex items-center justify-between text-xs">
                  <span className={darkMode ? "text-gray-400" : "text-gray-500"}>
                    {formatCountdown(item.dueDate)}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 font-medium ${
                    darkMode ? "bg-gray-800 text-gray-200" : "bg-white text-gray-600"
                  }`}>
                    {formatDate(item.dueDate)}
                  </span>
                </div>
              </button>
            );
          })}
      </div>
    </aside>
  );
}
