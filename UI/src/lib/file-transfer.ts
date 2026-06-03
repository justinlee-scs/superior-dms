import { isOfficeFilename, mimeTypeForFilename } from "@/lib/file-types";

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;

  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }

  return btoa(binary);
}

export async function saveResponseAsFile(response: Response, filename: string) {
  const safeName = filename || "download.bin";

  if (isOfficeFilename(safeName)) {
    const contentType =
      response.headers.get("Content-Type") || mimeTypeForFilename(safeName);
    const data = new Uint8Array(await response.arrayBuffer());
    const href = `data:${contentType};base64,${bytesToBase64(data)}`;
    const link = window.document.createElement("a");
    link.href = href;
    link.download = safeName;
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    return;
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = safeName;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

