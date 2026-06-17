const OFFICE_EXTENSIONS = new Set([".docx", ".xlsx", ".pptx"]);
const PDF_EXTENSION = ".pdf";

export function getFileExtension(filename: string): string {
  const lower = filename.toLowerCase();
  const dotIndex = lower.lastIndexOf(".");
  return dotIndex >= 0 ? lower.slice(dotIndex) : "";
}

export function isOfficeFilename(filename: string): boolean {
  return OFFICE_EXTENSIONS.has(getFileExtension(filename));
}

export function isPdfFilename(filename: string): boolean {
  return getFileExtension(filename) === PDF_EXTENSION;
}

export function mimeTypeForFilename(filename: string): string {
  switch (getFileExtension(filename)) {
    case ".docx":
      return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    case ".xlsx":
      return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    case ".pptx":
      return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
    case ".pdf":
      return "application/pdf";
    default:
      return "application/octet-stream";
  }
}

