import { useState } from "react";
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
import { Badge } from "@/app/components/ui/badge";
import { Plus, X } from "lucide-react";
import type { Document } from "./document-card";

interface WorkflowEditorProps {
  document: Document | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (documentId: string, workflow: string, notes: string) => void;
}

const WORKFLOW_STAGES = [
  "Draft",
  "In Review",
  "Pending Approval",
  "Approved",
  "Published",
  "Archived",
];

export function WorkflowEditor({
  document,
  open,
  onOpenChange,
  onSave,
}: WorkflowEditorProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState(
    document?.workflow || "Draft"
  );
  const [notes, setNotes] = useState("");
  const [assignees, setAssignees] = useState<string[]>([]);
  const [newAssignee, setNewAssignee] = useState("");

  const handleSave = () => {
    if (document) {
      onSave(document.id, selectedWorkflow, notes);
      onOpenChange(false);
      setNotes("");
      setAssignees([]);
    }
  };

  const addAssignee = () => {
    if (newAssignee.trim() && !assignees.includes(newAssignee.trim())) {
      setAssignees([...assignees, newAssignee.trim()]);
      setNewAssignee("");
    }
  };

  const removeAssignee = (assignee: string) => {
    setAssignees(assignees.filter((a) => a !== assignee));
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
            <Label htmlFor="workflow">Workflow Stage</Label>
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
            <Label htmlFor="assignees">Assignees</Label>
            <div className="flex gap-2">
              <input
                id="assignees"
                type="text"
                value={newAssignee}
                onChange={(e) => setNewAssignee(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && addAssignee()}
                placeholder="Add assignee email"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <Button type="button" size="sm" onClick={addAssignee}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {assignees.map((assignee) => (
                <Badge key={assignee} variant="secondary">
                  {assignee}
                  <button
                    onClick={() => removeAssignee(assignee)}
                    className="ml-1 hover:text-destructive"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              ))}
            </div>
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

          <div className="p-3 bg-gray-50 rounded-lg space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Current Stage:</span>
              <span>{document.workflow}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">New Stage:</span>
              <span className="font-medium">{selectedWorkflow}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
