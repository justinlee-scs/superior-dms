import { useEffect, useRef, useState } from "react";
import {
  Pen,
  Eraser,
  RotateCcw,
  Download,
  Save,
  X,
  Stamp,
  Plus,
  MousePointer2,
  Type,
} from "lucide-react";
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
const STAMP_SIZE_OPTIONS = [
  { label: "Small", value: 0.5 },
  { label: "Medium", value: 1 },
  { label: "Large", value: 1.5 },
] as const;
const DEFAULT_STAMP_SIZE = STAMP_SIZE_OPTIONS[1].value;
const DEFAULT_STAMP_OPACITY = 0.7;
const MAX_CUSTOM_STAMPS = 5;
const TEXT_BOX_MIN_WIDTH = 120;
const TEXT_BOX_MIN_HEIGHT = 40;
const TEXT_BOX_MAX_WIDTH = 260;
const TEXT_BOX_MAX_HEIGHT = 650;
const TEXT_BOX_MAX_CHARS = 255;
const TEXT_BOX_PADDING = 10;
const TEXT_BOX_FONT_SIZE = 14;
const TEXT_BOX_LINE_HEIGHT = 20;
const TEXTBOX_EDITOR_MIN_WIDTH = 220; // wide enough for char count + Cancel + Add buttons

const STAMP_COLORS: Record<string, string> = {
  APPROVED: "#006400",
  REJECTED: "#f00c1e",
  URGENT: "#f00c1e",
  DRAFT: "#0517b9",
  CONFIDENTIAL: "#f00c1e",
  POSTED: "#B80000",
};

interface PDFAnnotatorProps {
  document: Document;
  pdfBlob: Blob;
  onClose: () => void;
  onSaveVersion: (
    annotatedPdfBlob: Blob,
    layoutJson?: { customStamps?: string[] },
  ) => Promise<void>;
  darkMode?: boolean;
  currentUserName: string;
  canAccessStamps?: boolean;
  canCreateStampLabels?: boolean;
  canAccessTextBoxes?: boolean;
  layoutJson?: {
    customStamps?: string[];
  } | null;
}

// "select" is the neutral/no-drawing state — pointer behaves like a normal
// cursor over the page (no strokes, no erasing, no stamping). It exists so
// there's an explicit, labeled way to stop drawing, rather than overloading
// re-clicking an active tool or relying on toolMode defaulting to null.
type ToolMode = "select" | "pen" | "eraser" | "stamp" | "text";

// One annotation layer (as a dataURL snapshot of that page's overlay canvas)
// per PDF page number. Captured whenever the user navigates away from a page,
// and restored whenever they navigate back to it.
type AnnotationStore = Record<number, string>;

type AnnotationItem = StampAnnotation | TextBoxAnnotation;

type StampAnnotation = {
  id: string;
  type: "stamp";
  x: number;
  y: number;
  stampText: string;
  createdBy: string;
  createdAt: string;
  color: string;
  size: number;
};

type TextBoxAnnotation = {
  id: string;
  type: "text";
  x: number;
  y: number;
  text: string;
};

type BoxLayout = {
  visibleLines: string[];
  boxWidth: number;
  boxHeight: number;
  maxTextWidth: number;
  maxLines: number;
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string[] {
  const paragraphs = text.split(/\r?\n/);
  const lines: string[] = [];

  const pushWrappedWord = (word: string) => {
    let chunk = "";
    for (const char of word) {
      const next = chunk + char;
      if (chunk && ctx.measureText(next).width > maxWidth) {
        lines.push(chunk);
        chunk = char;
      } else {
        chunk = next;
      }
    }
    if (chunk) {
      lines.push(chunk);
    }
  };

  for (const paragraph of paragraphs) {
    const words = paragraph.split(/\s+/).filter(Boolean);
    if (words.length === 0) {
      lines.push("");
      continue;
    }

    let currentLine = "";
    for (const word of words) {
      if (!currentLine) {
        if (ctx.measureText(word).width <= maxWidth) {
          currentLine = word;
        } else {
          pushWrappedWord(word);
        }
        continue;
      }

      const next = `${currentLine} ${word}`;
      if (ctx.measureText(next).width <= maxWidth) {
        currentLine = next;
        continue;
      }

      lines.push(currentLine);
      if (ctx.measureText(word).width <= maxWidth) {
        currentLine = word;
      } else {
        pushWrappedWord(word);
        currentLine = "";
      }
    }
    if (currentLine) {
      lines.push(currentLine);
    }
  }

  return lines;
}

function measureTextBoxLayout(
  ctx: CanvasRenderingContext2D,
  text: string,
): BoxLayout {
  ctx.font = `${TEXT_BOX_FONT_SIZE}px Arial`;
  ctx.textAlign = "left";
  ctx.textBaseline = "top";

  const maxTextWidth = TEXT_BOX_MAX_WIDTH - TEXT_BOX_PADDING * 2;
  const maxLines = Math.max(
    1,
    Math.floor((TEXT_BOX_MAX_HEIGHT - TEXT_BOX_PADDING * 2) / TEXT_BOX_LINE_HEIGHT),
  );
  const wrappedLines = wrapText(ctx, text, maxTextWidth);
  const visibleLines = wrappedLines.slice(0, maxLines);

  if (wrappedLines.length > maxLines && visibleLines.length > 0) {
    const lastIndex = visibleLines.length - 1;
    let candidate = visibleLines[lastIndex];
    while (candidate.length > 0 && ctx.measureText(`${candidate}…`).width > maxTextWidth) {
      candidate = candidate.slice(0, -1);
    }
    visibleLines[lastIndex] = `${candidate}…`;
  }

  let maxLineWidth = 0;
  for (const line of visibleLines) {
    const width = ctx.measureText(line).width;
    if (width > maxLineWidth) maxLineWidth = width;
  }

  const boxWidth = Math.min(
    TEXT_BOX_MAX_WIDTH,
    Math.max(
      120,
      TEXT_BOX_PADDING * 2 + maxLineWidth,
    ),
  );

  const boxHeight = Math.min(
    TEXT_BOX_MAX_HEIGHT,
    Math.max(
      40,
      TEXT_BOX_PADDING * 2 + visibleLines.length * TEXT_BOX_LINE_HEIGHT,
    ),
  );

  return { visibleLines, boxWidth, boxHeight, maxTextWidth, maxLines };
}

function measureStampLayout(
  ctx: CanvasRenderingContext2D,
  stampText: string,
  createdBy: string,
  createdAt: string,
  size: number,
) {
  const titleFontSize = 14 + size * 4;
  const subFontSize = Math.max(10, Math.round(titleFontSize * 0.48));
  const lineHeight = subFontSize + 6;
  const titleHeight = titleFontSize + 4;
  const lines = [
    { text: stampText, font: `bold ${titleFontSize}px Arial` },
    { text: createdBy, font: `${subFontSize}px Arial` },
    { text: createdAt, font: `${subFontSize}px Arial` },
  ];

  let maxWidth = 0;
  for (const line of lines) {
    ctx.font = line.font;
    const width = ctx.measureText(line.text).width;
    if (width > maxWidth) maxWidth = width;
  }

  const totalHeight = titleHeight + lineHeight * 2;
  const boxWidth = maxWidth + 16;
  const boxHeight = totalHeight + 10;
  return {
    lines,
    boxWidth,
    boxHeight,
    titleFontSize,
    subFontSize,
    lineHeight,
    titleHeight,
    totalHeight,
  };
}

export function PDFAnnotator({
  document,
  pdfBlob,
  onClose,
  onSaveVersion,
  darkMode = false,
  currentUserName,
  canAccessStamps = true,
  canCreateStampLabels = true,
  canAccessTextBoxes = true,
  layoutJson = null,
}: PDFAnnotatorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const objectCanvasRef = useRef<HTMLCanvasElement>(null);
  const textEditorRef = useRef<HTMLTextAreaElement>(null);
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
  const [stampSize, setStampSize] = useState<number>(DEFAULT_STAMP_SIZE);
  const [stampInputValue, setStampInputValue] = useState("");
  const [showStampInput, setShowStampInput] = useState(false);
  const [zoom, setZoom] = useState(1);
  const zoomRef = useRef(1);
  const pageCanvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawingRef = useRef(false);
  const [draftTextBox, setDraftTextBox] = useState<{
    x: number;
    y: number;
    page: number;
    text: string;
  } | null>(null);

  // Per-page annotation snapshots, keyed by page number. Using a ref (not
  // state) because we read/write it synchronously around page navigation and
  // don't want renders triggered by it.
  const annotationsRef = useRef<AnnotationStore>({});
  const annotationItemsRef = useRef<Record<number, AnnotationItem[]>>({});
  const currentPageRef = useRef(1);
  const dragItemRef = useRef<{
    id: string;
    kind: AnnotationItem["type"];
    page: number;
    offsetX: number;
    offsetY: number;
  } | null>(null);

  useEffect(() => {
    const initialStamps = layoutJson?.customStamps?.filter(Boolean) ?? [];
    if (initialStamps.length === 0) return;

    setCustomStamps((current) => {
      const merged = Array.from(new Set([...current, ...initialStamps]));
      localStorage.setItem("pdf-annotator-stamps", JSON.stringify(merged));
      return merged;
    });
  }, [layoutJson]);

  useEffect(() => {
    if (draftTextBox) {
      textEditorRef.current?.focus();
    }
  }, [draftTextBox]);

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

  useEffect(() => {
    if (pdfdocRef.current) {
      renderPage(currentPageRef.current);
    }
  }, [zoom]);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

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
      const viewport = page.getViewport({ scale: zoom });

      const devicePixelRatio = window.devicePixelRatio || 1;

      const canvas = pageCanvasRef.current;
      canvas.width = Math.floor(viewport.width * devicePixelRatio);
      canvas.height = Math.floor(viewport.height * devicePixelRatio);

      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;

      const context = canvas.getContext("2d");
      if (!context) return;

      context.setTransform(
        devicePixelRatio,
        0,
        0,
        devicePixelRatio,
        0,
        0,
      );

      await page.render({
        canvasContext: context,
        viewport,
      }).promise;

      // Update drawing canvas size, then restore that page's annotations.
      if (canvasRef.current) {
        canvasRef.current.width = Math.floor(viewport.width * devicePixelRatio);
        canvasRef.current.height = Math.floor(viewport.height * devicePixelRatio);

        canvasRef.current.style.width = `${viewport.width}px`;
        canvasRef.current.style.height = `${viewport.height}px`;

        const ctx = canvasRef.current.getContext("2d");
        ctx?.setTransform(
          devicePixelRatio,
          0,
          0,
          devicePixelRatio,
          0,
          0,
        );
      }

      if (objectCanvasRef.current) {
        objectCanvasRef.current.width = Math.floor(viewport.width * devicePixelRatio);
        objectCanvasRef.current.height = Math.floor(viewport.height * devicePixelRatio);

        objectCanvasRef.current.style.width = `${viewport.width}px`;
        objectCanvasRef.current.style.height = `${viewport.height}px`;

        const ctx = objectCanvasRef.current.getContext("2d");
        ctx?.setTransform(
          devicePixelRatio,
          0,
          0,
          devicePixelRatio,
          0,
          0,
        );
      }
      await restoreAnnotations(pageNum);
      renderObjectLayer(pageNum);
      setDraftTextBox(null);

      currentPageRef.current = pageNum;
      setCurrentPage(pageNum);
    } catch (error) {
      toast.error(`Failed to render page ${pageNum}`);
      console.error(error);
    }
  };

  // Initialize top annotation canvas with mouse events.
  useEffect(() => {
    const canvas = objectCanvasRef.current;
    const penCanvas = canvasRef.current;
    if (!canvas || !penCanvas) return;

    const ctx = canvas.getContext("2d");
    const penCtx = penCanvas.getContext("2d");
    if (!ctx || !penCtx) return;

    let lastX = 0;
    let lastY = 0;

    const getPoint = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    };

    const renderDraggingItem = () => {
      renderObjectLayer(currentPageRef.current);
    };

    const handleMouseDown = (e: MouseEvent) => {
      const { x, y } = getPoint(e);

      if (toolMode === "select") {
        const hit = hitTestAnnotation(currentPageRef.current, x, y, ctx);
        if (!hit) return;

        dragItemRef.current = {
          id: hit.id,
          kind: hit.type,
          page: currentPageRef.current,
          offsetX: hit.type === "stamp" ? x - hit.x : x - hit.x,
          offsetY: hit.type === "stamp" ? y - hit.y : y - hit.y,
        };
        canvas.style.cursor = "grabbing";
        return;
      }

      if (toolMode === "stamp") {
        if (!canAccessStamps) return;
        addStampAnnotation(x, y);
        return;
      }

      if (toolMode === "text") {
        if (!canAccessTextBoxes) return;
        setDraftTextBox({
          x: clamp(
            x / zoomRef.current,
            0,
            canvas.width / zoomRef.current - TEXT_BOX_MIN_WIDTH,
          ),
          y: clamp(
            y / zoomRef.current,
            0,
            canvas.height / zoomRef.current - TEXT_BOX_MIN_HEIGHT,
          ),
          page: currentPageRef.current,
          text: "",
        });
        return;
      }

      lastX = x;
      lastY = y;
      isDrawingRef.current = true;
    };

    const handleMouseMove = (e: MouseEvent) => {
      const { x, y } = getPoint(e);

      if (dragItemRef.current) {
        const page = dragItemRef.current.page;
        const items = annotationItemsRef.current[page] ?? [];
        const item = items.find((entry) => entry.id === dragItemRef.current?.id);
        if (!item) return;

        if (item.type === "stamp") {
          const layout = measureStampLayout(
            ctx,
            item.stampText,
            item.createdBy,
            item.createdAt,
            item.size,
          );
          item.x = clamp(
            (x - dragItemRef.current.offsetX) / zoomRef.current,
            layout.boxWidth / 2,
            canvas.width - layout.boxWidth / 2,
          );
          item.y = clamp(
            (y - dragItemRef.current.offsetY) / zoomRef.current,
            layout.boxHeight / 2,
            canvas.height - layout.boxHeight / 2,
          );
        } else {
          const layout = measureTextBoxLayout(ctx, item.text);
          item.x = clamp(
            (x - dragItemRef.current.offsetX) / zoomRef.current,
            0,
            Math.max(0, canvas.width - layout.boxWidth),
          );
          item.y = clamp(
            (y - dragItemRef.current.offsetY) / zoomRef.current,
            0,
            Math.max(0, canvas.height - layout.boxHeight),
          );
        }

        renderDraggingItem();
        canvas.style.cursor = "grabbing";
        return;
      }

      if (
        !isDrawingRef.current ||
        toolMode === "select" ||
        toolMode === "stamp" ||
        toolMode === "text"
      ) {
        return;
      }

      penCtx.lineCap = "round";
      penCtx.lineJoin = "round";
      penCtx.lineWidth = penWidth;

      if (toolMode === "pen") {
        penCtx.globalCompositeOperation = "source-over";
        penCtx.strokeStyle = penColor;
        penCtx.beginPath();
        penCtx.moveTo(lastX, lastY);
        penCtx.lineTo(x, y);
        penCtx.stroke();
      } else if (toolMode === "eraser") {
        penCtx.globalCompositeOperation = "destination-out";
        penCtx.strokeStyle = "rgba(0,0,0,1)";
        penCtx.beginPath();
        penCtx.moveTo(lastX, lastY);
        penCtx.lineTo(x, y);
        penCtx.stroke();
      }

      lastX = x;
      lastY = y;
    };

    const handleMouseUp = () => {
      isDrawingRef.current = false;
      dragItemRef.current = null;
      canvas.style.cursor = toolMode === "text" ? "text" : toolMode === "stamp" ? "cell" : "default";
      renderObjectLayer(currentPageRef.current);
    };

    const handleMouseLeave = () => {
      isDrawingRef.current = false;
      dragItemRef.current = null;
      renderObjectLayer(currentPageRef.current);
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
  }, [toolMode, penColor, penWidth, selectedStamp, stampSize, canAccessStamps, canAccessTextBoxes, currentUserName]);

  // Helper function to draw stamp text on canvas, including the author
  // name and current system date as additional lines beneath the main
  // stamp label (e.g. "POSTED" / "Justin Lee" / "06/18/2026").
  const drawStamp = (
    ctx: CanvasRenderingContext2D,
    stampText: string,
    x: number,
    y: number,
    size: number,
  ) => {
    const now = new Date();
    const dateStr = `${String(now.getMonth() + 1).padStart(2, "0")}/${String(
      now.getDate(),
    ).padStart(2, "0")}/${now.getFullYear()}`;

    const stampColor = STAMP_COLORS[stampText] ?? penColor;

    const titleFontSize = 14 + size * 4;
    const subFontSize = Math.max(10, Math.round(titleFontSize * 0.48));
    const lineHeight = subFontSize + 6;
    const titleHeight = titleFontSize + 4;

    const lines = [
      { text: stampText, font: `bold ${titleFontSize}px Arial` },
      { text: currentUserName, font: `${subFontSize}px Arial` },
      { text: dateStr, font: `${subFontSize}px Arial` },
    ];

    ctx.save();
    ctx.globalAlpha = DEFAULT_STAMP_OPACITY;
    ctx.globalCompositeOperation = "source-over";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    let maxWidth = 0;
    for (const line of lines) {
      ctx.font = line.font;
      const w = ctx.measureText(line.text).width;
      if (w > maxWidth) maxWidth = w;
    }

    const totalHeight = titleHeight + lineHeight * 2;
    const boxWidth = maxWidth + 16;
    const boxHeight = totalHeight + 10;

    ctx.fillStyle = "rgba(255, 255, 255, 0.82)";
    ctx.fillRect(x - boxWidth / 2, y - boxHeight / 2, boxWidth, boxHeight);

    ctx.strokeStyle = stampColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(x - boxWidth / 2, y - boxHeight / 2, boxWidth, boxHeight);

    let cursorY = y - totalHeight / 2 + titleHeight / 2;
    ctx.fillStyle = stampColor;
    ctx.font = lines[0].font;
    ctx.fillText(lines[0].text, x, cursorY);

    cursorY += titleHeight / 2 + lineHeight / 2;
    ctx.font = lines[1].font;
    ctx.fillText(lines[1].text, x, cursorY);

    cursorY += lineHeight;
    ctx.font = lines[2].font;
    ctx.fillText(lines[2].text, x, cursorY);
    ctx.restore();
  };

  const drawTextBox = (
    ctx: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
  ) => {
    const safeText = text.trim();
    if (!safeText) return;

    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    const { visibleLines, boxWidth, boxHeight, maxTextWidth } = measureTextBoxLayout(ctx, safeText);
    const boxX = clamp(x, 0, Math.max(0, ctx.canvas.width - boxWidth));
    const boxY = clamp(y, 0, Math.max(0, ctx.canvas.height - boxHeight));

    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.fillRect(boxX, boxY, boxWidth, boxHeight);

    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

    ctx.fillStyle = "#111827";
    ctx.beginPath();
    ctx.rect(boxX, boxY, boxWidth, boxHeight);
    ctx.clip();
    visibleLines.forEach((line, index) => {
      ctx.fillText(
        line,
        boxX + TEXT_BOX_PADDING,
        boxY + TEXT_BOX_PADDING + index * TEXT_BOX_LINE_HEIGHT,
      );
    });

    ctx.restore();
  };

  const commitTextBox = () => {
    if (!draftTextBox) return;
    const page = draftTextBox.page;
    const nextItem: TextBoxAnnotation = {
      id: crypto.randomUUID(),
      type: "text",
      x: draftTextBox.x,
      y: draftTextBox.y,
      text: draftTextBox.text,
    };
    annotationItemsRef.current[page] = [
      ...(annotationItemsRef.current[page] ?? []),
      nextItem,
    ];
    renderObjectLayer(page);
    setDraftTextBox(null);
  };

  const drawStampAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: StampAnnotation,
  ) => {
    const layout = measureStampLayout(
      ctx,
      annotation.stampText,
      annotation.createdBy,
      annotation.createdAt,
      annotation.size,
    );

    ctx.save();
    ctx.globalAlpha = DEFAULT_STAMP_OPACITY;
    ctx.globalCompositeOperation = "source-over";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const x = annotation.x * zoomRef.current;
    const y = annotation.y * zoomRef.current;

    const boxX = x - layout.boxWidth / 2;
    const boxY = y - layout.boxHeight / 2;

    ctx.fillStyle = "rgba(255, 255, 255, 0.82)";
    ctx.fillRect(boxX, boxY, layout.boxWidth, layout.boxHeight);

    ctx.strokeStyle = annotation.color;
    ctx.lineWidth = 2;
    ctx.strokeRect(boxX, boxY, layout.boxWidth, layout.boxHeight);

    let cursorY = y - layout.totalHeight / 2 + layout.titleHeight / 2;
    ctx.fillStyle = annotation.color;
    ctx.font = layout.lines[0].font;
    ctx.fillText(layout.lines[0].text, x, cursorY);

    cursorY += layout.titleHeight / 2 + layout.lineHeight / 2;
    ctx.font = layout.lines[1].font;
    ctx.fillText(layout.lines[1].text, x, cursorY);

    cursorY += layout.lineHeight;
    ctx.font = layout.lines[2].font;
    ctx.fillText(layout.lines[2].text, x, cursorY);
    ctx.restore();
  };

  const drawTextAnnotation = (
    ctx: CanvasRenderingContext2D,
    annotation: TextBoxAnnotation,
  ) => {
    const safeText = annotation.text.trim();
    if (!safeText) return;

    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    const { visibleLines, boxWidth, boxHeight } = measureTextBoxLayout(ctx, safeText);

    const x = annotation.x * zoomRef.current;
    const y = annotation.y * zoomRef.current;
    const boxX = x;
    const boxY = y;

    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.fillRect(boxX, boxY, boxWidth, boxHeight);

    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

    ctx.fillStyle = "#111827";
    ctx.beginPath();
    ctx.rect(boxX, boxY, boxWidth, boxHeight);
    ctx.clip();
    visibleLines.forEach((line, index) => {
      ctx.fillText(
        line,
        boxX + TEXT_BOX_PADDING,
        boxY + TEXT_BOX_PADDING + index * TEXT_BOX_LINE_HEIGHT,
      );
    });

    ctx.restore();
  };

  const renderObjectLayer = (pageNum: number) => {
    const canvas = objectCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const items = annotationItemsRef.current[pageNum] ?? [];
    for (const item of items) {
      if (item.type === "stamp") {
        drawStampAnnotation(ctx, item);
      } else {
        drawTextAnnotation(ctx, item);
      }
    }
  };

  const hitTestAnnotation = (
    pageNum: number,
    x: number,
    y: number,
    ctx: CanvasRenderingContext2D,
  ): AnnotationItem | null => {
    const pdfX = x / zoomRef.current;
    const pdfY = y / zoomRef.current;

    const items = annotationItemsRef.current[pageNum] ?? [];

    for (let i = items.length - 1; i >= 0; i--) {
      const item = items[i];

      if (item.type === "text") {
        const layout = measureTextBoxLayout(ctx, item.text.trim());

        if (
          pdfX >= item.x &&
          pdfX <= item.x + layout.boxWidth &&
          pdfY >= item.y &&
          pdfY <= item.y + layout.boxHeight
        ) {
          return item;
        }
      } else {
        const layout = measureStampLayout(
          ctx,
          item.stampText,
          item.createdBy,
          item.createdAt,
          item.size,
        );

        const left = item.x - layout.boxWidth / 2;
        const top = item.y - layout.boxHeight / 2;

        if (
          pdfX >= left &&
          pdfX <= left + layout.boxWidth &&
          pdfY >= top &&
          pdfY <= top + layout.boxHeight
        ) {
          return item;
        }
      }
    }

    return null;
  };

  const addStampAnnotation = (x: number, y: number) => {
    const page = currentPageRef.current;
    const item: StampAnnotation = {
      id: crypto.randomUUID(),
      type: "stamp",
      x: x / zoomRef.current,
      y: y / zoomRef.current,
      stampText: selectedStamp,
      createdBy: currentUserName,
      createdAt: new Date().toLocaleDateString(),
      color: STAMP_COLORS[selectedStamp] ?? penColor,
      size: stampSize,
    };
    annotationItemsRef.current[page] = [
      ...(annotationItemsRef.current[page] ?? []),
      item,
    ];
    renderObjectLayer(page);
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
    if (!canCreateStampLabels) return;
    if (!stampInputValue.trim()) return;
    const newStamp = stampInputValue.toUpperCase().trim();
    if (customStamps.length >= MAX_CUSTOM_STAMPS) {
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
    if (!canCreateStampLabels) return;
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
    if (objectCanvasRef.current) {
      const objectCtx = objectCanvasRef.current.getContext("2d");
      if (objectCtx) {
        objectCtx.clearRect(0, 0, objectCanvasRef.current.width, objectCanvasRef.current.height);
      }
    }
    setDraftTextBox(null);
    // Also clear the stored snapshot for this page so navigating away and
    // back doesn't resurrect the cleared annotations.
    delete annotationsRef.current[currentPageRef.current];
    delete annotationItemsRef.current[currentPageRef.current];
  };

  // Build a full multi-page PDF: for every page, re-render the PDF page at
  // export quality (scale 1.0), composite that page's annotation layer
  // (captured at display scale 1.5) on top scaled down to match, and embed
  // the result as a page in a new pdf-lib document.
  // Using EXPORT_SCALE=1.0 prevents scale from compounding on each save
  // round-trip (the previous bug: saving at 1.5× each time → 1.5^n zoom).
  const buildAnnotatedPdf = async (): Promise<Uint8Array<ArrayBuffer>> => {
    if (!pdfdocRef.current) throw new Error("PDF not loaded");

    if (draftTextBox) {
      commitTextBox();
    }

    // Make sure the page we're currently viewing is captured too.
    captureAnnotations(currentPageRef.current);

    const EXPORT_SCALE = 1.0; // change back to 1.0 if scaling issues persist

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
      // const snapshot = annotationsRef.current[pageNum];
      const snapshot = annotationsRef.current[pageNum];
      if (snapshot) {
        await new Promise<void>((resolve) => {
          const img = new Image();
          img.onload = () => {
            baseCtx.drawImage(
              img,
              0, 0,
              img.naturalWidth, img.naturalHeight,
              0, 0,
              exportViewport.width, exportViewport.height
            );
            resolve();
          };
          img.onerror = () => resolve();
          img.src = snapshot;
        });
      }

      const items = annotationItemsRef.current[pageNum] ?? [];
      const previousZoom = zoomRef.current;
      zoomRef.current = 1;
      for (const item of items) {
        if (item.type === "stamp") {
          drawStampAnnotation(baseCtx, item);
        } else {
          drawTextAnnotation(baseCtx, item);
        }
      }
      zoomRef.current = previousZoom;

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

      await onSaveVersion(blob, { customStamps });
      toast.success("Annotations saved as new version");
      onClose();
    } catch (error) {
      toast.error("Failed to save as version");
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const textBoxPreviewLayout = (() => {
    const canvas = canvasRef.current ?? pageCanvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!ctx) {
      return {
        boxWidth: Math.max(TEXT_BOX_MIN_WIDTH, TEXTBOX_EDITOR_MIN_WIDTH),
        boxHeight: TEXT_BOX_MIN_HEIGHT,
      };
    }

    const previewText = draftTextBox?.text.trim() || "Write a comment...";
    const layout = measureTextBoxLayout(ctx, previewText);
    return {
      boxWidth: Math.max(layout.boxWidth, TEXTBOX_EDITOR_MIN_WIDTH),
      boxHeight: layout.boxHeight,
    };
  })();

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
          {canAccessStamps && (
            <Button
              variant={toolMode === "stamp" ? "default" : "outline"}
              size="sm"
              onClick={() => setToolMode("stamp")}
            >
              <Stamp className="w-4 h-4 mr-1" />
              Stamp
            </Button>
          )}
          {canAccessTextBoxes && (
            <Button
              variant={toolMode === "text" ? "default" : "outline"}
              size="sm"
              onClick={() => setToolMode("text")}
            >
              <Type className="w-4 h-4 mr-1" />
              Text
            </Button>
          )}
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

        {toolMode === "stamp" && canAccessStamps && (
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
                    {canCreateStampLabels && (
                      <button
                        onClick={() => removeStamp(stamp)}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition"
                        title="Remove stamp"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            {canCreateStampLabels && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowStampInput(!showStampInput)}
                className="text-xs"
              >
                <Plus className="w-3 h-3 mr-1" />
                New
              </Button>
            )}
            {showStampInput && canCreateStampLabels && (
              <div className="flex gap-1">
                <input
                  type="text"
                  value={stampInputValue}
                  onChange={(e) => setStampInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addCustomStamp()}
                  placeholder="New stamp..."
                  className={`px-2 py-1 rounded text-sm ${darkMode
                    ? "bg-gray-800 text-white border-gray-600"
                    : "bg-white text-black border-gray-300"
                    } border`}
                  autoFocus
                  maxLength={15}
                />
                <Button size="sm" onClick={addCustomStamp}>
                  Add
                </Button>
              </div>
            )}
            <div className="flex items-center gap-1">
              {STAMP_SIZE_OPTIONS.map((option) => (
                <Button
                  key={option.label}
                  variant={stampSize === option.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStampSize(option.value)}
                  className="text-xs"
                >
                  {option.label}
                </Button>
              ))}
            </div>
            {!DEFAULT_STAMPS.includes(selectedStamp) && (
              <input
                type="color"
                value={penColor}
                onChange={(e) => setPenColor(e.target.value)}
                className="w-8 h-8 rounded cursor-pointer"
                title="Stamp color"
              />
            )}
            <span className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
              Opacity fixed at 70%
            </span>
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
            className={`absolute top-0 left-0 ${toolMode === "pen"
              ? "cursor-crosshair"
              : toolMode === "eraser"
                ? "cursor-pointer"
                : toolMode === "stamp"
                  ? "cursor-cell"
                  : toolMode === "text"
                    ? "cursor-text"
                    : "cursor-default"
              }`}
          />
          <canvas
            ref={objectCanvasRef}
            className={`absolute top-0 left-0 ${toolMode === "pen"
              ? "cursor-crosshair"
              : toolMode === "eraser"
                ? "cursor-pointer"
                : toolMode === "stamp"
                  ? "cursor-cell"
                  : toolMode === "text"
                    ? "cursor-text"
                    : toolMode === "select"
                      ? "cursor-move"
                      : "cursor-default"
              }`}
          />
          {draftTextBox && canAccessTextBoxes && (
            <div
              className="absolute z-20 rounded-lg border border-gray-700/40 bg-white/75 p-2 shadow-lg backdrop-blur-sm"
              style={{
                left: clamp(
                  draftTextBox.x,
                  0,
                  Math.max(0, (pageCanvasRef.current?.width ?? TEXT_BOX_MAX_WIDTH) - textBoxPreviewLayout.boxWidth),
                ),
                top: clamp(
                  draftTextBox.y,
                  0,
                  Math.max(0, (pageCanvasRef.current?.height ?? TEXT_BOX_MAX_HEIGHT) - textBoxPreviewLayout.boxHeight),
                ),
                width: textBoxPreviewLayout.boxWidth,
                maxWidth: TEXT_BOX_MAX_WIDTH,
                maxHeight: TEXT_BOX_MAX_HEIGHT,
              }}
            >
              <textarea
                ref={textEditorRef}
                value={draftTextBox.text}
                onChange={(e) =>
                  setDraftTextBox((current) =>
                    current
                      ? { ...current, text: e.target.value.slice(0, TEXT_BOX_MAX_CHARS) }
                      : current,
                  )
                }
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    setDraftTextBox(null);
                  }
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                    commitTextBox();
                  }
                }}
                maxLength={TEXT_BOX_MAX_CHARS}
                placeholder="Write a comment..."
                className="block w-full resize-none rounded-md border border-gray-300 bg-white/70 px-3 py-2 text-sm text-gray-900 outline-none"
                style={{
                  width: "100%",
                  maxWidth: TEXT_BOX_MAX_WIDTH - TEXT_BOX_PADDING * 2,
                  maxHeight: TEXT_BOX_MAX_HEIGHT - 72,
                  height: Math.max(
                    24,
                    textBoxPreviewLayout.boxHeight - 72,
                  ),
                  minHeight: 0,
                  overflow: "hidden",
                  overflowWrap: "anywhere",
                  wordBreak: "break-word",
                  whiteSpace: "pre-wrap",
                  fontFamily: "Arial, sans-serif",
                  lineHeight: `${TEXT_BOX_LINE_HEIGHT}px`,
                }}
              />
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="text-xs text-gray-500">
                  {draftTextBox.text.length}/{TEXT_BOX_MAX_CHARS}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDraftTextBox(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={commitTextBox}
                    disabled={!draftTextBox.text.trim()}
                  >
                    Add
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer - Page Navigation */}
      <div className={`relative flex items-center justify-center gap-4 p-4 border-t ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
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
          className={`w-12 px-2 py-1 rounded text-center ${darkMode
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
        <div className="absolute right-4 flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
          >
            -
          </Button>

          <span className="w-16 text-center text-sm">
            {Math.round(zoom * 100)}%
          </span>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
          >
            +
          </Button>
        </div>
      </div>
    </div>
  );
}
