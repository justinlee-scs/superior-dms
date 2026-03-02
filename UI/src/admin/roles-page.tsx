import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Checkbox } from "@/app/components/ui/checkbox";

import {
  addManagedRole,
  copyRolePermissions,
  createRole,
  getRole,
  listManagedRoles,
  listPermissions,
  listRoles,
  removeManagedRole,
  setRolePermissions,
  type Permission,
  type Role,
} from "@/lib/rbac";

export default function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [selectedPermissionKeys, setSelectedPermissionKeys] = useState<Set<string>>(new Set());
  const [managedRoleIds, setManagedRoleIds] = useState<Set<string>>(new Set());
  const [copySourceRoleId, setCopySourceRoleId] = useState<string>("");
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleDescription, setNewRoleDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedRole = useMemo(
    () => roles.find((role) => role.id === selectedRoleId) ?? null,
    [roles, selectedRoleId],
  );

  const loadBase = async () => {
    const [rolesData, permissionsData] = await Promise.all([listRoles(), listPermissions()]);
    setRoles(rolesData);
    setPermissions(permissionsData);
    if (!selectedRoleId && rolesData.length > 0) {
      setSelectedRoleId(rolesData[0].id);
    }
  };

  const loadRoleDetails = async (roleId: string) => {
    const [roleWithPermissions, managedRoles] = await Promise.all([getRole(roleId), listManagedRoles(roleId)]);
    setSelectedPermissionKeys(new Set(roleWithPermissions.permissions.map((permission) => permission.key)));
    setManagedRoleIds(new Set(managedRoles.map((role) => role.id)));
  };

  useEffect(() => {
    loadBase().catch(() => toast.error("Failed to load roles and permissions"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRoleId) return;
    loadRoleDetails(selectedRoleId).catch(() => toast.error("Failed to load role details"));
  }, [selectedRoleId]);

  const onCreateRole = async () => {
    const trimmed = newRoleName.trim();
    if (!trimmed) {
      toast.error("Role name is required");
      return;
    }
    setLoading(true);
    try {
      const role = await createRole({
        name: trimmed,
        description: newRoleDescription.trim() || undefined,
      });
      await loadBase();
      setSelectedRoleId(role.id);
      setNewRoleName("");
      setNewRoleDescription("");
      toast.success("Role created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create role");
    } finally {
      setLoading(false);
    }
  };

  const onTogglePermission = (permissionKey: string, checked: boolean) => {
    setSelectedPermissionKeys((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(permissionKey);
      } else {
        next.delete(permissionKey);
      }
      return next;
    });
  };

  const onSavePermissions = async () => {
    if (!selectedRoleId) return;
    setLoading(true);
    try {
      await setRolePermissions(selectedRoleId, Array.from(selectedPermissionKeys));
      await loadRoleDetails(selectedRoleId);
      toast.success("Role permissions updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update role permissions");
    } finally {
      setLoading(false);
    }
  };

  const onCopyFromRole = async () => {
    if (!selectedRoleId || !copySourceRoleId) return;
    if (selectedRoleId === copySourceRoleId) {
      toast.error("Select a different source role");
      return;
    }
    setLoading(true);
    try {
      await copyRolePermissions(selectedRoleId, copySourceRoleId);
      await loadRoleDetails(selectedRoleId);
      toast.success("Permissions copied");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to copy permissions");
    } finally {
      setLoading(false);
    }
  };

  const onToggleManagedRole = async (managedRoleId: string, checked: boolean) => {
    if (!selectedRoleId) return;
    setLoading(true);
    try {
      if (checked) {
        await addManagedRole(selectedRoleId, managedRoleId);
      } else {
        await removeManagedRole(selectedRoleId, managedRoleId);
      }
      await loadRoleDetails(selectedRoleId);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update role hierarchy");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-4 rounded border p-4">
        <div className="text-sm font-semibold">Roles</div>
        <div className="space-y-2 max-h-72 overflow-auto">
          {roles.map((role) => (
            <button
              key={role.id}
              type="button"
              onClick={() => setSelectedRoleId(role.id)}
              className={`w-full rounded border px-3 py-2 text-left text-sm ${
                role.id === selectedRoleId ? "border-blue-600 bg-blue-50" : "hover:bg-gray-50"
              }`}
            >
              {role.name}
            </button>
          ))}
        </div>

        <div className="space-y-2 border-t pt-4">
          <div className="text-sm font-semibold">Create role</div>
          <Input
            placeholder="Role name"
            value={newRoleName}
            onChange={(event) => setNewRoleName(event.target.value)}
          />
          <Input
            placeholder="Description (optional)"
            value={newRoleDescription}
            onChange={(event) => setNewRoleDescription(event.target.value)}
          />
          <Button onClick={onCreateRole} disabled={loading} className="w-full">
            + Add role
          </Button>
        </div>
      </div>

      <div className="space-y-4 rounded border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">
            {selectedRole ? `Role: ${selectedRole.name}` : "Select a role"}
          </div>
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded border px-2 text-sm"
              value={copySourceRoleId}
              onChange={(event) => setCopySourceRoleId(event.target.value)}
              disabled={!selectedRoleId || loading}
            >
              <option value="">Copy permissions from role</option>
              {roles
                .filter((role) => role.id !== selectedRoleId)
                .map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
            </select>
            <Button onClick={onCopyFromRole} disabled={!selectedRoleId || !copySourceRoleId || loading}>
              Copy role
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-semibold">Permissions</div>
          <div className="grid gap-2 sm:grid-cols-2">
            {permissions.map((permission) => (
              <label key={permission.id} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
                <Checkbox
                  checked={selectedPermissionKeys.has(permission.key)}
                  disabled={!selectedRoleId || loading}
                  onCheckedChange={(checked) => onTogglePermission(permission.key, checked === true)}
                />
                <span>{permission.key}</span>
              </label>
            ))}
          </div>
          <Button onClick={onSavePermissions} disabled={!selectedRoleId || loading}>
            Save permissions
          </Button>
        </div>

        <div className="space-y-2 border-t pt-4">
          <div className="text-sm font-semibold">Hierarchy</div>
          <div className="text-xs text-gray-500">Checked roles are managed by the selected role.</div>
          <div className="grid gap-2 sm:grid-cols-2">
            {roles
              .filter((role) => role.id !== selectedRoleId)
              .map((role) => (
                <label key={role.id} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
                  <Checkbox
                    checked={managedRoleIds.has(role.id)}
                    disabled={!selectedRoleId || loading}
                    onCheckedChange={(checked) => onToggleManagedRole(role.id, checked === true)}
                  />
                  <span>{role.name}</span>
                </label>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
