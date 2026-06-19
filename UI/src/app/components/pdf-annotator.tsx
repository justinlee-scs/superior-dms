import { useEffect, useRef, useState } from "react";
import { Pen, Eraser, RotateCcw, Download, Save, X, Stamp, Plus, MousePointer2 } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { toast } from "sonner";
import type { Document } from "@/app/components/document-card";
import { PDFDocument } from "pdf-lib";

// PDF.js loaded dynamically
let pdfjsLib: any = null;

const loadPdfJs = async () => {
  if (!pdfjsLib) {
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
    document.head.appendChild(script);

    return new Promise((resolve) => {
      script.onload = () => {
        pdfjsLib = (window as any).pdfjsLib;
        pdfjsLib.GlobalWorkerOptions.workerSrc =
          "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        resolve(pdfjsLib);
      };
    });
  }
  return pdfjsLib;
};

const DEFAULT_STAMPS = ["APPROVED", "REJECTED", "URGENT", "DRAFT", "CONFIDENTIAL", "POSTED"];

interface PDFAnnotatorProps {
  document: Document;
  pdfBlob: Blob;
  onClose: () => void;
  onSaveVersion: (annotatedPdfBlob: Blob) => Promise<void>;
  darkMode?: boolean;
  currentUserName: string;
}

// "select" is the neutral/no-drawing state — pointer behaves like a normal
// cursor over the page (no strokes, no erasing, no stamping). It exists so
// there's an explicit, labeled way to stop drawing, rather than overloading
// re-clicking an active tool or relying on toolMode defaulting to null.
type ToolMode = "select" | "pen" | "eraser" | "stamp";

// One annotation layer (as a dataURL snapshot of that page's overlay canvas)
// per PDF page number. Captured whenever the user navigates away from a page,
// and restored whenever they navigate back to it.
type AnnotationStore = Record<number, string>;

export function PDFAnnotator({
  document,
  pdfBlob,
  onClose,
  onSaveVersion,
  darkMode = false,
  currentUserName,
}: PDFAnnotatorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfdocRef = useRef<any>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [toolMode, setToolMode] = useState<ToolMode>("select");
  const [penColor, setPenColor] = useState("#000000");
  const [penWidth, setPenWidth] = useState(2);
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [savedColors, setSavedColors] = useState<string[]>(() => {
    const stored = localStorage.getItem("pdf-annotator-colors");
    return stored ? JSON.parse(stored) : ["#000000", "#FF0000", "#0000FF", "#00AA00", "#FFAA00"];
  });
  const [selectedStamp, setSelectedStamp] = useState<string>(DEFAULT_STAMPS[0]);
  const [customStamps, setCustomStamps] = useState<string[]>(() => {
    const stored = localStorage.getItem("pdf-annotator-stamps");
    return stored ? JSON.parse(stored) : [];
  });
  const [stampInputValue, setStampInputValue] = useState("");
  const [showStampInput, setShowStampInput] = useState(false);
  const pageCanvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);

  // Per-page annotation snapshots, keyed by page number. Using a ref (not
  // state) because we read/write it synchronously around page navigation and
  // don't want renders triggered by it.
  const annotationsRef = useRef<AnnotationStore>({});
  const currentPageRef = useRef(1);

  // Initialize PDF.js
  useEffect(() => {
    const loadPdf = async () => {
      try {
        await loadPdfJs();
        const arrayBuffer = await pdfBlob.arrayBuffer();
        const pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        pdfdocRef.current = pdfDoc;
        setTotalPages(pdfDoc.numPages);
        await renderPage(1);
      } catch (error) {
        toast.error("Failed to load PDF");
        console.error(error);
      }
    };

    loadPdf();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdfBlob]);

  // Snapshot whatever is currently drawn on the annotation canvas into the
  // store under the given page number.
  const captureAnnotations = (pageNum: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    annotationsRef.current[pageNum] = canvas.toDataURL("image/png");
  };

  // Restore a page's annotation snapshot onto the (already-sized) overlay
  // canvas, or clear it if there's nothing saved for that page yet.
  const restoreAnnotations = async (pageNum: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const snapshot = annotationsRef.current[pageNum];
    if (!snapshot) return;

    await new Promise<void>((resolve) => {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve();
      };
      img.onerror = () => resolve();
      img.src = snapshot;
    });
  };

  const renderPage = async (pageNum: number) => {
    if (!pdfdocRef.current || !pageCanvasRef.current) return;

    // Save the page we're leaving before we touch anything else.
    captureAnnotations(currentPageRef.current);

    try {
      const page = await pdfdocRef.current.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.5 });

      const canvas = pageCanvasRef.current;
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      const context = canvas.getContext("2d");
      if (!context) return;

      await page.render({
        canvasContext: context,
        viewport: viewport,
      }).promise;

      // Update drawing canvas size, then restore that page's annotations.
      if (canvasRef.current) {
        canvasRef.current.width = viewport.width;
        canvasRef.current.height = viewport.height;
      }
      await restoreAnnotations(pageNum);

      currentPageRef.current = pageNum;
      setCurrentPage(pageNum);
    } catch (error) {
      toast.error(`Failed to render page ${pageNum}`);
      console.error(error);
    }
  };

  // Initialize drawing canvas with mouse events
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let lastX = 0;
    let lastY = 0;

    const handleMouseDown = (e: MouseEvent) => {
      if (toolMode === "select") return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (toolMode === "stamp") {
        // Draw stamp at click location
        drawStamp(ctx, selectedStamp, x, y, penWidth);
        return;
      }

      lastX = x;
      lastY = y;
      isDrawingRef.current = true;
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDrawingRef.current || toolMode === "select" || toolMode === "stamp") return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.lineWidth = penWidth;

      if (toolMode === "pen") {
        ctx.globalCompositeOperation = "source-over";
        ctx.strokeStyle = penColor;
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(x, y);
        ctx.stroke();
      } else if (toolMode === "eraser") {
        ctx.globalCompositeOperation = "destination-out";
        ctx.strokeStyle = "rgba(0,0,0,1)";
        ctx.beginPath();
        ctx.moveTo(lastX, lastY);
        ctx.lineTo(x, y);
        ctx.stroke();
      }

      lastX = x;
      lastY = y;
    };

    const handleMouseUp = () => {
      isDrawingRef.current = false;
    };

    const handleMouseLeave = () => {
      isDrawingRef.current = false;
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
      canvas.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [toolMode, penColor, penWidth, selectedStamp]);

  // Helper function to draw stamp text on canvas, including the author
  // name and current system date as additional lines beneath the main
  // stamp label (e.g. "POSTED" / "Justin Lee" / "06/18/2026").
  const drawStamp = (ctx: CanvasRenderingContext2D, stampText: string, x: number, y: number, size: number) => {
    const now = new Date();
    const dateStr = `${String(now.getMonth() + 1).padStart(2, "0")}/${String(now.getDate()).padStart(2, "0")}/${now.getFullYear()}`;

    const titleFontSize = 20 + size * 2;
    const subFontSize = Math.max(10, Math.round(titleFontSize * 0.5));

    const lines = [
      { text: stampText, font: `bold ${titleFontSize}px Arial` },
      { text: currentUserName, font: `${subFontSize}px Arial` },
      { text: dateStr, font: `${subFontSize}px Arial` },
    ];

    ctx.globalCompositeOperation = "source-over";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // Measure the widest line and total stacked height first, so the
    // background box fits all three lines.
    let maxWidth = 0;
    for (const line of lines) {
      ctx.font = line.font;
      const w = ctx.measureText(line.text).width;
      if (w > maxWidth) maxWidth = w;
    }

    const lineHeight = subFontSize + 6;
    const titleHeight = titleFontSize + 4;
    const totalHeight = titleHeight + lineHeight * 2;

    const boxWidth = maxWidth + 16;
    const boxHeight = totalHeight + 10;

    ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
    ctx.fillRect(x - boxWidth / 2, y - boxHeight / 2, boxWidth, boxHeight);

    ctx.strokeStyle = penColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(x - boxWidth / 2, y - boxHeight / 2, boxWidth, boxHeight);

    // Draw each line, stacked top-to-bottom, vertically centered as a group.
    let cursorY = y - totalHeight / 2 + titleHeight / 2;
    ctx.fillStyle = penColor;
    ctx.font = lines[0].font;
    ctx.fillText(lines[0].text, x, cursorY);

    cursorY += titleHeight / 2 + lineHeight / 2;
    ctx.font = lines[1].font;
    ctx.fillText(lines[1].text, x, cursorY);

    cursorY += lineHeight;
    ctx.font = lines[2].font;
    ctx.fillText(lines[2].text, x, cursorY);
  };

  // Save current color to favorites
  const saveColor = () => {
    if (savedColors.includes(penColor)) return;
    if (savedColors.length >= 5) {
      const newColors = [...savedColors.slice(1), penColor];
      setSavedColors(newColors);
      localStorage.setItem("pdf-annotator-colors", JSON.stringify(newColors));
    } else {
      const newColors = [...savedColors, penColor];
      setSavedColors(newColors);
      localStorage.setItem("pdf-annotator-colors", JSON.stringify(newColors));
    }
    toast.success("Color saved!");
  };

  // Remove saved color
  const removeColor = (color: string) => {
    const newColors = savedColors.filter((c) => c !== color);
    setSavedColors(newColors);
    localStorage.setItem("pdf-annotator-colors", JSON.stringify(newColors));
  };

  // Add custom stamp
  const addCustomStamp = () => {
    if (!stampInputValue.trim()) return;
    const newStamp = stampInputValue.toUpperCase().trim();
    if (customStamps.length >= 5) {
      const updated = [...customStamps.slice(1), newStamp];
      setCustomStamps(updated);
      localStorage.setItem("pdf-annotator-stamps", JSON.stringify(updated));
    } else {
      const updated = [...customStamps, newStamp];
      setCustomStamps(updated);
      localStorage.setItem("pdf-annotator-stamps", JSON.stringify(updated));
    }
    setStampInputValue("");
    setShowStampInput(false);
    toast.success("Stamp added!");
  };

  // Remove custom stamp
  const removeStamp = (stamp: string) => {
    const newStamps = customStamps.filter((s) => s !== stamp);
    setCustomStamps(newStamps);
    localStorage.setItem("pdf-annotator-stamps", JSON.stringify(newStamps));
  };

  const handleClearAnnotations = () => {
    if (!canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
    // Also clear the stored snapshot for this page so navigating away and
    // back doesn't resurrect the cleared annotations.
    delete annotationsRef.current[currentPageRef.current];
  };

  // Build a full multi-page PDF: for every page, re-render the PDF page at
  // export quality (scale 1.0), composite that page's annotation layer
  // (captured at display scale 1.5) on top scaled down to match, and embed
  // the result as a page in a new pdf-lib document.
  // Using EXPORT_SCALE=1.0 prevents scale from compounding on each save
  // round-trip (the previous bug: saving at 1.5× each time → 1.5^n zoom).
  const buildAnnotatedPdf = async (): Promise<Uint8Array<ArrayBuffer>> => {
    if (!pdfdocRef.current) throw new Error("PDF not loaded");

    // Make sure the page we're currently viewing is captured too.
    captureAnnotations(currentPageRef.current);

    const EXPORT_SCALE = 1.0; // keep at 1.0 — display scale (1.5) must NOT be used here

    const outPdf = await PDFDocument.create();

    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      const page = await pdfdocRef.current.getPage(pageNum);

      // Export at 1:1 — this is what gets embedded in the PDF.
      const exportViewport = page.getViewport({ scale: EXPORT_SCALE });

      const baseCanvas = window.document.createElement("canvas");
      baseCanvas.width = exportViewport.width;
      baseCanvas.height = exportViewport.height;
      const baseCtx = baseCanvas.getContext("2d");
      if (!baseCtx) throw new Error("Failed to get canvas context");

      await page.render({ canvasContext: baseCtx, viewport: exportViewport }).promise;

      // Composite annotation snapshot — it was captured at display scale (1.5×),
      // so draw it scaled down to fit the export canvas dimensions exactly.
      const snapshot = annotationsRef.current[pageNum];
      if (snapshot) {
        await new Promise<void>((resolve) => {
          const img = new Image();
          img.onload = () => {
            baseCtx.drawImage(
              img,
              0, 0,
              img.naturalWidth, img.naturalHeight,  // source: full display-size snapshot
              0, 0,
              exportViewport.width, exportViewport.height  // dest: export-size canvas
            );
            resolve();
          };
          img.onerror = () => resolve();
          img.src = snapshot;
        });
      }

      const pngDataUrl = baseCanvas.toDataURL("image/png");
      const pngBytes = await fetch(pngDataUrl).then((r) => r.arrayBuffer());
      const embeddedImage = await outPdf.embedPng(pngBytes);

      const outPage = outPdf.addPage([exportViewport.width, exportViewport.height]);
      outPage.drawImage(embeddedImage, {
        x: 0,
        y: 0,
        width: exportViewport.width,
        height: exportViewport.height,
      });
    }

    const pdfBytes = await outPdf.save();
    // pdf-lib's return type is Uint8Array<ArrayBufferLike>, which TS treats
    // as possibly SharedArrayBuffer-backed. The DOM's BlobPart type requires
    // an ArrayBuffer-backed view specifically, and merely re-wrapping with
    // `new Uint8Array(pdfBytes)` does NOT narrow the type (TS still infers
    // ArrayBufferLike from the source). Instead, copy the bytes into a
    // freshly-allocated, explicitly-typed ArrayBuffer.
    const arrayBuffer = new ArrayBuffer(pdfBytes.byteLength);
    new Uint8Array(arrayBuffer).set(pdfBytes);
    return new Uint8Array(arrayBuffer);
  };

  const handleDownloadAnnotated = async () => {
    setIsDownloading(true);
    try {
      const pdfBytes = await buildAnnotatedPdf();
      const blob = new Blob([pdfBytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `${document.name}-annotated.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error("Failed to download annotated PDF");
      console.error(error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleSaveAsVersion = async () => {
    setIsSaving(true);
    try {
      const pdfBytes = await buildAnnotatedPdf();
      const blob = new Blob([pdfBytes], { type: "application/pdf" });

      await onSaveVersion(blob);
      toast.success("Annotations saved as new version");
      onClose();
    } catch (error) {
      toast.error("Failed to save as version");
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={`flex flex-col h-screen ${darkMode ? "bg-gray-900 text-white" : "bg-white"}`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
        <div>
          <h2 className="text-xl font-semibold">{document.name}</h2>
          <p className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
            Page {currentPage} of {totalPages}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Toolbar */}
      <div className={`flex items-center gap-2 p-4 border-b ${darkMode ? "border-gray-700" : "border-gray-200"} flex-wrap`}>
        <div className="flex items-center gap-2">
          <Button
            variant={toolMode === "select" ? "default" : "outline"}
            size="sm"
            onClick={() => setToolMode("select")}
            title="Stop drawing — pan/scroll and click around without marking the page"
          >
            <MousePointer2 className="w-4 h-4 mr-1" />
            Select
          </Button>
          <Button
            variant={toolMode === "pen" ? "default" : "outline"}
            size="sm"
            onClick={() => setToolMode("pen")}
          >
            <Pen className="w-4 h-4 mr-1" />
            Pen
          </Button>
          <Button
            variant={toolMode === "eraser" ? "default" : "outline"}
            size="sm"
            onClick={() => setToolMode("eraser")}
          >
            <Eraser className="w-4 h-4 mr-1" />
            Eraser
          </Button>
          <Button
            variant={toolMode === "stamp" ? "default" : "outline"}
            size="sm"
            onClick={() => setToolMode("stamp")}
          >
            <Stamp className="w-4 h-4 mr-1" />
            Stamp
          </Button>
        </div>

        {toolMode === "pen" && (
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={penColor}
              onChange={(e) => setPenColor(e.target.value)}
              className="w-10 h-10 rounded cursor-pointer"
              title="Pen color"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={saveColor}
              className="text-xs"
            >
              <Plus className="w-3 h-3" />
            </Button>
            <input
              type="range"
              min="1"
              max="20"
              value={penWidth}
              onChange={(e) => setPenWidth(Number(e.target.value))}
              className="w-24"
              title="Pen width"
            />
            <span className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
              {penWidth}px
            </span>
          </div>
        )}

        {toolMode === "eraser" && (
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="1"
              max="20"
              value={penWidth}
              onChange={(e) => setPenWidth(Number(e.target.value))}
              className="w-24"
              title="Eraser width"
            />
            <span className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
              {penWidth}px
            </span>
          </div>
        )}

        {toolMode === "pen" && savedColors.length > 0 && (
          <div className="flex items-center gap-1">
            {savedColors.map((color) => (
              <div key={color} className="relative group">
                <button
                  onClick={() => setPenColor(color)}
                  className={`w-8 h-8 rounded border-2 ${penColor === color ? "border-white" : "border-gray-400"}`}
                  style={{ backgroundColor: color }}
                  title={color}
                />
                <button
                  onClick={() => removeColor(color)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition"
                  title="Remove color"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {toolMode === "stamp" && (
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1 flex-wrap max-w-xs">
              {DEFAULT_STAMPS.map((stamp) => (
                <Button
                  key={stamp}
                  variant={selectedStamp === stamp ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedStamp(stamp)}
                  className="text-xs"
                >
                  {stamp}
                </Button>
              ))}
            </div>
            {customStamps.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {customStamps.map((stamp) => (
                  <div key={stamp} className="relative group">
                    <Button
                      variant={selectedStamp === stamp ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedStamp(stamp)}
                      className="text-xs"
                    >
                      {stamp}
                    </Button>
                    <button
                      onClick={() => removeStamp(stamp)}
                      className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition"
                      title="Remove stamp"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowStampInput(!showStampInput)}
              className="text-xs"
            >
              <Plus className="w-3 h-3 mr-1" />
              New
            </Button>
            {showStampInput && (
              <div className="flex gap-1">
                <input
                  type="text"
                  value={stampInputValue}
                  onChange={(e) => setStampInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addCustomStamp()}
                  placeholder="New stamp..."
                  className={`px-2 py-1 rounded text-sm ${
                    darkMode ? "bg-gray-800 text-white border-gray-600" : "bg-white text-black border-gray-300"
                  } border`}
                  autoFocus
                  maxLength={15}
                />
                <Button size="sm" onClick={addCustomStamp}>
                  Add
                </Button>
              </div>
            )}
            <input
              type="color"
              value={penColor}
              onChange={(e) => setPenColor(e.target.value)}
              className="w-8 h-8 rounded cursor-pointer"
              title="Stamp color"
            />
          </div>
        )}

        <div className="flex-1" />

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearAnnotations}
          >
            <RotateCcw className="w-4 h-4 mr-1" />
            Clear
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadAnnotated}
            disabled={isDownloading}
          >
            <Download className="w-4 h-4 mr-1" />
            {isDownloading ? "Preparing..." : "Download"}
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleSaveAsVersion}
            disabled={isSaving}
          >
            <Save className="w-4 h-4 mr-1" />
            {isSaving ? "Saving..." : "Save Version"}
          </Button>
        </div>
      </div>

      {/* PDF Canvas Container */}
      <div className="flex-1 overflow-auto flex items-start justify-center" ref={containerRef}>
        <div className="relative">
          <canvas
            ref={pageCanvasRef}
            className={`${darkMode ? "bg-gray-800" : "bg-white"} shadow-lg`}
          />
          <canvas
            ref={canvasRef}
            className={`absolute top-0 left-0 ${
              toolMode === "pen"
                ? "cursor-crosshair"
                : toolMode === "eraser"
                  ? "cursor-pointer"
                  : toolMode === "stamp"
                    ? "cursor-cell"
                    : "cursor-default"
            }`}
          />
        </div>
      </div>

      {/* Footer - Page Navigation */}
      <div className={`flex items-center justify-center gap-4 p-4 border-t ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
        <Button
          variant="outline"
          size="sm"
          onClick={() => renderPage(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
        >
          Previous
        </Button>
        <input
          type="number"
          min="1"
          max={totalPages}
          value={currentPage}
          onChange={(e) => {
            const page = Math.min(totalPages, Math.max(1, Number(e.target.value)));
            renderPage(page);
          }}
          className={`w-12 px-2 py-1 rounded text-center ${
            darkMode
              ? "bg-gray-800 text-white border-gray-600"
              : "bg-white text-black border-gray-300"
          } border`}
        />
        <span className={`${darkMode ? "text-gray-400" : "text-gray-600"}`}>
          / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => renderPage(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage === totalPages}
        >
          Next
        </Button>
      </div>
    </div>
  );
}