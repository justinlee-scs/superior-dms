import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/app/components/ui/dialog";
import { Button } from "@/app/components/ui/button";
import { Label } from "@/app/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";
import { Textarea } from "@/app/components/ui/textarea";
import type { Document } from "./document-card";

interface WorkflowEditorProps {
  document: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (
    documentId: string,
    workflow: "failed" | "pending" | "uploaded" | "needs review",
    notes: string,
  ) => Promise<void>;
}

const WORKFLOW_STAGES: Array<"failed" | "pending" | "uploaded" | "needs review"> = [
  "failed",
  "pending",
  "uploaded",
  "needs review",
];

export function WorkflowEditor({
  document,
  open,
  onOpenChange,
  onSave,
}: WorkflowEditorProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<
    "failed" | "pending" | "uploaded" | "needs review"
  >("pending");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!document || !open) return;
    const wf = document.workflow.toLowerCase();
    if (wf === "failed" || wf === "pending" || wf === "uploaded" || wf === "needs review") {
      setSelectedWorkflow(wf);
    } else {
      setSelectedWorkflow("pending");
    }
    setNotes(document.workflowNotes ?? "");
  }, [document, open]);

  const handleSave = async () => {
    if (document) {
      setSaving(true);
      try {
        await onSave(document.id, selectedWorkflow, notes);
        onOpenChange(false);
      } finally {
        setSaving(false);
      }
    }
  };

  if (!document) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Workflow</DialogTitle>
          <DialogDescription>
            Update the workflow status for {document.name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="workflow">Workflow Status</Label>
            <Select value={selectedWorkflow} onValueChange={setSelectedWorkflow}>
              <SelectTrigger id="workflow">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WORKFLOW_STAGES.map((stage) => (
                  <SelectItem key={stage} value={stage}>
                    {stage}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add workflow notes..."
              rows={4}
            />
          </div>

        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
