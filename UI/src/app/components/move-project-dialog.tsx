import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/app/components/ui/dialog";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import { FolderInput } from "lucide-react";

interface MoveProjectDialogProps {
  /** Controls whether the dialog is open. When used from the bulk bar the
   *  trigger button is rendered internally; when used from a dropdown menu
   *  the caller controls open state via these props. */
  open: boolean;
  onOpenChange: (open: boolean) => void;
  availableTags: string[];
  darkMode?: boolean;
  onApply: (projectName: string) => Promise<void>;
}

export function MoveProjectDialog({
  open,
  onOpenChange,
  availableTags,
  darkMode,
  onApply,
}: MoveProjectDialogProps) {
  const [projectInput, setProjectInput] = useState("");
  const [applying, setApplying] = useState(false);

  const existingProjects = Array.from(
    new Set(
      availableTags
        .filter((t) => t.startsWith("project:"))
        .map((t) => t.slice("project:".length).trim())
        .filter(Boolean),
    ),
  ).sort();

  const handleApply = async () => {
    const trimmed = projectInput.trim();
    if (!trimmed) return;
    setApplying(true);
    try {
      await onApply(trimmed);
      setProjectInput("");
      onOpenChange(false);
    } finally {
      setApplying(false);
    }
  };

  // Reset input when dialog closes
  const handleOpenChange = (next: boolean) => {
    if (!next) setProjectInput("");
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className={`sm:max-w-[400px] ${darkMode ? "border-gray-700 bg-gray-800 text-gray-100" : ""}`}
      >
        <DialogHeader>
          <DialogTitle>Move to Project</DialogTitle>
          <DialogDescription className={darkMode ? "text-gray-400" : ""}>
            The selected document(s) will be moved to this project. Existing
            project tags will be replaced.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="space-y-1.5">
            <Label className="text-sm">Project name</Label>
            <Input
              value={projectInput}
              onChange={(e) => setProjectInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleApply()}
              placeholder="e.g. alpha-site or Q3 Audit"
              className={
                darkMode
                  ? "border-gray-600 bg-gray-700 text-gray-100 placeholder:text-gray-400"
                  : ""
              }
            />
            <p
              className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}
            >
              The <code>project:</code> prefix is added automatically.
            </p>
          </div>

          {existingProjects.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs opacity-60">Existing projects</Label>
              <div className="flex flex-wrap gap-1.5">
                {existingProjects.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setProjectInput(p)}
                    className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors hover:border-blue-400 hover:text-blue-600 ${
                      projectInput === p
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : darkMode
                          ? "border-gray-600 text-gray-300"
                          : "border-gray-300 text-gray-600"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            className={darkMode ? "border-gray-600" : ""}
          >
            Cancel
          </Button>
          <Button
            onClick={handleApply}
            disabled={applying || !projectInput.trim()}
          >
            {applying ? "Moving…" : "Move"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Self-contained trigger + dialog for use in the bulk action bar. */
export function MoveProjectDialogWithTrigger({
  availableTags,
  darkMode,
  disabled,
  onApply,
}: Omit<MoveProjectDialogProps, "open" | "onOpenChange"> & {
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        size="sm"
        variant="outline"
        className="gap-1.5"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        <FolderInput className="h-3.5 w-3.5" />
        Move Project
      </Button>

      <MoveProjectDialog
        open={open}
        onOpenChange={setOpen}
        availableTags={availableTags}
        darkMode={darkMode}
        onApply={onApply}
      />
    </>
  );
}