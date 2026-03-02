import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog";
import { getCurrentUserProfile, updateCurrentUserProfile } from "@/lib/profile";

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    getCurrentUserProfile()
      .then((user) => {
        setUsername(user.username || "");
        setEmail(user.email || "");
      })
      .catch(() => toast.error("Failed to load profile"));
  }, [open]);

  const onSave = async () => {
    const payload: {
      username?: string;
      current_password?: string;
      new_password?: string;
    } = {};

    if (username.trim()) payload.username = username.trim();

    if (newPassword || currentPassword || confirmPassword) {
      if (!currentPassword || !newPassword) {
        toast.error("Enter current and new password");
        return;
      }
      if (newPassword !== confirmPassword) {
        toast.error("New password and confirmation do not match");
        return;
      }
      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }

    setLoading(true);
    try {
      const updated = await updateCurrentUserProfile(payload);
      sessionStorage.setItem("user", JSON.stringify(updated));
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Profile updated");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update profile");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Profile</DialogTitle>
          <DialogDescription>Change username and password.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <Input value={email} disabled />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Username</label>
            <Input value={username} onChange={(event) => setUsername(event.target.value)} />
          </div>
          <div className="border-t pt-3">
            <p className="mb-2 text-sm font-medium">Change password</p>
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Current password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
              <Input
                type="password"
                placeholder="New password (min 8 chars)"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
              <Input
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
              />
            </div>
          </div>
          <Button className="w-full" onClick={onSave} disabled={loading}>
            Save Profile
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
