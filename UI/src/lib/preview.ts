export type PreviewWindowController = {
  finish: (content: Blob | string) => void;
  fail: () => void;
};

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function openLoadingPreviewWindow(
  title: string,
): PreviewWindowController | null {
  const previewWindow = window.open("", "_blank");
  if (!previewWindow) return null;

  previewWindow.document.open();
  previewWindow.document.write(`
    <html>
      <head>
        <title>${escapeHtml(title)}</title>
      </head>
      <body style="margin:0;display:flex;align-items:center;justify-content:center;font-family:sans-serif;background:#fff;color:#111827;">
        <div style="text-align:center;">
          <div style="width:36px;height:36px;border:4px solid #d1d5db;border-top-color:#2563eb;border-radius:9999px;animation:spin 1s linear infinite;margin:0 auto 10px;"></div>
          <div>Loading preview...</div>
          <div id="elapsed" style="font-size:12px;color:#6b7280;margin-top:4px;">0s</div>
        </div>
        <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
      </body>
    </html>
  `);
  previewWindow.document.close();

  const startedAt = Date.now();
  const timerId = window.setInterval(() => {
    if (previewWindow.closed) {
      window.clearInterval(timerId);
      return;
    }

    const elapsedEl = previewWindow.document.getElementById("elapsed");
    if (elapsedEl) {
      elapsedEl.textContent = `${Math.floor((Date.now() - startedAt) / 1000)}s`;
    }
  }, 300);

  const cleanup = () => {
    window.clearInterval(timerId);
  };

  const finish = (content: Blob | string) => {
    if (previewWindow.closed) {
      cleanup();
      return;
    }

    if (typeof content === "string") {
      previewWindow.document.open();
      previewWindow.document.write(content);
      previewWindow.document.close();
    } else {
      const url = window.URL.createObjectURL(content);
      previewWindow.location.replace(url);
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
    }
    cleanup();
  };

  const fail = () => {
    cleanup();
    if (!previewWindow.closed) {
      previewWindow.close();
    }
  };

  return { finish, fail };
}
