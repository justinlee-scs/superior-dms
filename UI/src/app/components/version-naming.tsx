export function buildVersionedFilename(
  filename: string,
  versionNumber?: number | null,
): string {
  if (!versionNumber) return filename;

  const lastDot = filename.lastIndexOf(".");
  if (lastDot === -1) return `${filename}_v${versionNumber}`;

  const name = filename.slice(0, lastDot);
  const ext = filename.slice(lastDot);

  return `${name}_v${versionNumber}${ext}`;
}
