export function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const precision = value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(precision)} ${units[unitIndex]}`;
}

export function formatPageCount(count?: number | null): string {
  if (!count || count <= 0) return "—";
  return count === 1 ? "1 page" : `${count} pages`;
}

export function formatLocalDateFromDateOnly(dateOnly?: string | null): string {
  if (!dateOnly) return "—";
  const [year, month, day] = dateOnly.split("-").map(Number);
  if (!year || !month || !day) return dateOnly;
  return new Date(year, month - 1, day).toLocaleDateString();
}
