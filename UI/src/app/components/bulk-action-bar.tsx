import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/app/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/app/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/app/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import {
  X,
  Tag,
  GitBranch,
  Trash2,
  ChevronDown,
  Plus,
  Minus,
  Download,
  RefreshCw,
} from "lucide-react";
import type { Document } from "@/app/components/document-card";
import { MoveProjectDialogWithTrigger } from "@/app/components/move-project-dialog";

type WorkflowStatus = "failed" | "uploaded" | "needs review";

const WORKFLOW_STAGES: WorkflowStatus[] = ["failed", "uploaded", "needs review"];

interface BulkActionBarProps {
  documents: Document[];
  darkMode?: boolean;
  count: number;
  availableTags: string[];
  canDelete?: boolean;
  onDownload: () => void;
  onReprocess: () => void;
  onDelete: () => void;
  onClear: () => void;
  onBulkAddTags: (tags: string[]) => Promise<void>;
  onBulkRemoveTags: (tags: string[]) => Promise<void>;
  onBulkSetWorkflow: (status: WorkflowStatus) => Promise<void>;
  onBulkMoveProject: (projectName: string) => Promise<void>;
  /** Ref exposed so CompactProjectView can call .focus() on the bar */
  barRef?: React.RefObject<HTMLDivElement | null>;
  /** Called when Escape is pressed inside the bar */
  onEscapeToTable?: () => void;
}

// ─── Tag Popover ─────────────────────────────────────────────────────────────

function TagPopover({
  availableTags,
  darkMode,
  disabled,
  onApply,
}: {
  availableTags: string[];
  darkMode?: boolean;
  disabled?: boolean;
  onApply: (toAdd: string[], toRemove: string[]) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [addTags, setAddTags] = useState<string[]>([]);
  const [removeTags, setRemoveTags] = useState<string[]>([]);
  const [addInput, setAddInput] = useState("");
  const [removeInput, setRemoveInput] = useState("");
  const [applying, setApplying] = useState(false);

  const nonProjectTags = availableTags.filter((t) => !t.startsWith("project:"));

  const addSuggestions = nonProjectTags.filter(
    (t) =>
      t.toLowerCase().includes(addInput.toLowerCase()) &&
      !addTags.includes(t) &&
      addInput.length > 0,
  );

  const removeSuggestions = nonProjectTags.filter(
    (t) =>
      t.toLowerCase().includes(removeInput.toLowerCase()) &&
      !removeTags.includes(t) &&
      removeInput.length > 0,
  );

  const handleApply = async () => {
    if (!addTags.length && !removeTags.length) return;
    setApplying(true);
    try {
      await onApply(addTags, removeTags);
      setAddTags([]);
      setRemoveTags([]);
      setAddInput("");
      setRemoveInput("");
      setOpen(false);
    } finally {
      setApplying(false);
    }
  };

  const pill =
    "inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium";

  return (
    <Popover open={open} onOpenChange={disabled ? undefined : setOpen}>
      <PopoverTrigger asChild>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={disabled}
        >
          <Tag className="h-3.5 w-3.5" />
          Tags
          <ChevronDown className="h-3 w-3 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className={`w-80 p-4 ${darkMode ? "border-gray-700 bg-gray-800 text-gray-100" : ""}`}
        align="start"
      >
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider opacity-50">
          Bulk Edit Tags
        </p>

        {/* Add section */}
        <div className="mb-4">
          <Label className="mb-1.5 flex items-center gap-1.5 text-xs">
            <Plus className="h-3 w-3 text-green-500" />
            Add to all selected
          </Label>
          <div className="relative">
            <Input
              value={addInput}
              onChange={(e) => setAddInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && addInput.trim()) {
                  const val = addInput.trim();
                  if (!addTags.includes(val)) setAddTags((p) => [...p, val]);
                  setAddInput("");
                }
              }}
              placeholder="Type tag, press Enter…"
              className={`h-8 text-sm ${darkMode ? "border-gray-600 bg-gray-700 text-gray-100 placeholder:text-gray-400" : ""}`}
            />
            {addSuggestions.length > 0 && (
              <div
                className={`absolute z-50 mt-1 w-full rounded-md border shadow-md ${darkMode ? "border-gray-600 bg-gray-700" : "border-gray-200 bg-white"}`}
              >
                {addSuggestions.slice(0, 6).map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`w-full px-3 py-1.5 text-left text-sm hover:bg-blue-50 ${darkMode ? "hover:bg-gray-600" : ""}`}
                    onClick={() => {
                      setAddTags((p) => [...p, t]);
                      setAddInput("");
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>
          {addTags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {addTags.map((t) => (
                <span
                  key={t}
                  className={`${pill} bg-green-100 text-green-800 ${darkMode ? "bg-green-900/40 text-green-300" : ""}`}
                >
                  {t}
                  <button
                    type="button"
                    onClick={() => setAddTags((p) => p.filter((x) => x !== t))}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Remove section */}
        <div className="mb-4">
          <Label className="mb-1.5 flex items-center gap-1.5 text-xs">
            <Minus className="h-3 w-3 text-red-500" />
            Remove from all selected
          </Label>
          <div className="relative">
            <Input
              value={removeInput}
              onChange={(e) => setRemoveInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && removeInput.trim()) {
                  const val = removeInput.trim();
                  if (!removeTags.includes(val))
                    setRemoveTags((p) => [...p, val]);
                  setRemoveInput("");
                }
              }}
              placeholder="Type tag, press Enter…"
              className={`h-8 text-sm ${darkMode ? "border-gray-600 bg-gray-700 text-gray-100 placeholder:text-gray-400" : ""}`}
            />
            {removeSuggestions.length > 0 && (
              <div
                className={`absolute z-50 mt-1 w-full rounded-md border shadow-md ${darkMode ? "border-gray-600 bg-gray-700" : "border-gray-200 bg-white"}`}
              >
                {removeSuggestions.slice(0, 6).map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`w-full px-3 py-1.5 text-left text-sm hover:bg-red-50 ${darkMode ? "hover:bg-gray-600" : ""}`}
                    onClick={() => {
                      setRemoveTags((p) => [...p, t]);
                      setRemoveInput("");
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            )}
          </div>
          {removeTags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {removeTags.map((t) => (
                <span
                  key={t}
                  className={`${pill} bg-red-100 text-red-800 ${darkMode ? "bg-red-900/40 text-red-300" : ""}`}
                >
                  {t}
                  <button
                    type="button"
                    onClick={() =>
                      setRemoveTags((p) => p.filter((x) => x !== t))
                    }
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <Button
          size="sm"
          className="w-full"
          disabled={applying || (!addTags.length && !removeTags.length)}
          onClick={handleApply}
        >
          {applying ? "Applying…" : "Apply to selected"}
        </Button>
      </PopoverContent>
    </Popover>
  );
}

// ─── Workflow Popover ─────────────────────────────────────────────────────────

function WorkflowPopover({
  darkMode,
  disabled,
  onApply,
}: {
  darkMode?: boolean;
  disabled?: boolean;
  onApply: (status: WorkflowStatus) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<WorkflowStatus>("uploaded");
  const [applying, setApplying] = useState(false);

  const handleApply = async () => {
    setApplying(true);
    try {
      await onApply(status);
      setOpen(false);
    } finally {
      setApplying(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={disabled ? undefined : setOpen}>
      <PopoverTrigger asChild>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={disabled}
        >
          <GitBranch className="h-3.5 w-3.5" />
          Workflow
          <ChevronDown className="h-3 w-3 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className={`w-64 p-4 ${darkMode ? "border-gray-700 bg-gray-800 text-gray-100" : ""}`}
        align="start"
      >
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider opacity-50">
          Set Workflow Status
        </p>
        <Select
          value={status}
          onValueChange={(v) => setStatus(v as WorkflowStatus)}
        >
          <SelectTrigger
            className={`mb-3 h-8 text-sm ${darkMode ? "border-gray-600 bg-gray-700 text-gray-100" : ""}`}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent
            className={
              darkMode ? "border-gray-600 bg-gray-700 text-gray-100" : ""
            }
          >
            {WORKFLOW_STAGES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          className="w-full"
          disabled={applying}
          onClick={handleApply}
        >
          {applying ? "Applying…" : "Apply to selected"}
        </Button>
      </PopoverContent>
    </Popover>
  );
}

// ─── Delete Confirm Dialog ────────────────────────────────────────────────────

function DeleteConfirmDialog({
  count,
  darkMode,
  onConfirm,
}: {
  count: number;
  darkMode?: boolean;
  onConfirm: () => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        size="sm"
        variant="destructive"
        className="gap-1.5"
        onClick={() => setOpen(true)}
      >
        <Trash2 className="h-3.5 w-3.5" />
        Delete
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className={`sm:max-w-[380px] ${darkMode ? "border-gray-700 bg-gray-800 text-gray-100" : ""}`}
        >
          <DialogHeader>
            <DialogTitle>
              Delete {count} document{count !== 1 ? "s" : ""}?
            </DialogTitle>
            <DialogDescription className={darkMode ? "text-gray-400" : ""}>
              This will permanently delete {count} selected document
              {count !== 1 ? "s" : ""}. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              className={darkMode ? "border-gray-600" : ""}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setOpen(false);
                onConfirm();
              }}
            >
              Delete {count} document{count !== 1 ? "s" : ""}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ─── BulkActionBar ────────────────────────────────────────────────────────────

export function BulkActionBar({
  count,
  darkMode,
  availableTags,
  canDelete = false,
  onDownload,
  onReprocess,
  onDelete,
  onClear,
  onBulkAddTags,
  onBulkRemoveTags,
  onBulkSetWorkflow,
  onBulkMoveProject,
  barRef,
  onEscapeToTable,
}: BulkActionBarProps) {
  const inactive = count === 0;
  const internalRef = useRef<HTMLDivElement>(null);
  const ref = barRef ?? internalRef;

  const handleTagApply = async (toAdd: string[], toRemove: string[]) => {
    if (toAdd.length) await onBulkAddTags(toAdd);
    if (toRemove.length) await onBulkRemoveTags(toRemove);
  };

  // Arrow Left/Right roving focus between bar buttons
  const handleBarKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onEscapeToTable?.();
      return;
    }

    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

    const current = document.activeElement as HTMLElement | null;

    // Don't hijack arrow keys while typing in a text field (e.g. tag input) —
    // let native text-cursor movement happen instead of roving focus.
    if (current && (current.tagName === "INPUT" || current.tagName === "TEXTAREA")) {
      return;
    }

    // Popover/Dialog content renders into a portal physically outside the
    // bar's DOM subtree (even though it's still inside BulkActionBar in the
    // React tree, which is why this handler still fires for it). Without this,
    // bar.querySelectorAll() can't see Apply/Cancel/Delete buttons inside an
    // open popover or dialog, and arrow keys yank focus back to the toolbar.
    const portalScope = current?.closest<HTMLElement>(
      '[data-radix-popper-content-wrapper], [role="dialog"]'
    );

    const scope = portalScope ?? ref.current;
    if (!scope) return;

    const focusable = Array.from(
      scope.querySelectorAll<HTMLElement>(
        "button:not([disabled]), [role='button']:not([disabled])"
      )
    );
    if (!focusable.length) return;

    const idx = focusable.indexOf(current as HTMLElement);
    if (idx === -1) {
      focusable[0].focus();
      return;
    }

    e.preventDefault();
    const next =
      e.key === "ArrowRight"
        ? focusable[(idx + 1) % focusable.length]
        : focusable[(idx - 1 + focusable.length) % focusable.length];
    next.focus();
  }, [ref, onEscapeToTable]);

  return (
    <div
      ref={ref}
      onKeyDown={handleBarKeyDown}
      // Makes the bar itself focusable so B-key jump lands here,
      // then immediately moves to first button via focus delegation below
      tabIndex={-1}
      onFocus={(e) => {
        // If focus landed on the bar container itself (not a child button),
        // forward it to the first focusable button
        if (e.target === e.currentTarget) {
          const first = e.currentTarget.querySelector<HTMLElement>(
            "button:not([disabled])"
          );
          first?.focus();
        }
      }}
      className={`hidden md:flex flex-nowrap overflow-x-auto items-center gap-2 px-4 py-2 text-sm transition-opacity sm:px-8 rounded-2xl ${darkMode
          ? "border-gray-600 bg-gray-800/60"
          : "border-gray-300 bg-gray-100"
        } ${inactive ? "pointer-events-none select-none opacity-40" : "opacity-100"}`}
    >
      <span
        className={`mr-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${darkMode ? "bg-gray-700 text-gray-200" : "bg-gray-200 text-gray-700"
          }`}
      >
        {inactive ? "None selected" : `${count} selected`}
      </span>

      {/* Divider */}
      <span className={`h-4 w-px ${darkMode ? "bg-gray-600" : "bg-gray-300"}`} />

      <Button size="sm" className="gap-1.5" onClick={onDownload}>
        <Download className="h-3.5 w-3.5" />
        Download
      </Button>

      <Button size="sm" variant="outline" className="gap-1.5" onClick={onReprocess}>
        <RefreshCw className="h-3.5 w-3.5" />
        Reprocess
      </Button>

      {/* Divider */}
      <span className={`h-4 w-px ${darkMode ? "bg-gray-600" : "bg-gray-300"}`} />

      <TagPopover
        availableTags={availableTags}
        darkMode={darkMode}
        disabled={inactive}
        onApply={handleTagApply}
      />

      <WorkflowPopover
        darkMode={darkMode}
        disabled={inactive}
        onApply={onBulkSetWorkflow}
      />

      <MoveProjectDialogWithTrigger
        availableTags={availableTags}
        darkMode={darkMode}
        disabled={inactive}
        onApply={onBulkMoveProject}
      />

      {/* Divider */}
      <span className={`h-4 w-px ${darkMode ? "bg-gray-600" : "bg-gray-300"}`} />

      {canDelete && (
        <DeleteConfirmDialog
          count={count}
          darkMode={darkMode}
          onConfirm={onDelete}
        />
      )}

      <Button size="sm" variant="ghost" onClick={onClear}>
        Unselect All
      </Button>
    </div>
  );
}