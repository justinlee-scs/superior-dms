import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/app/components/ui/button";
import { Checkbox } from "@/app/components/ui/checkbox";
import { Input } from "@/app/components/ui/input";

import {
  createUser,
  getUserPermissions,
  listPermissions,
  listRoles,
  listUsers,
  resetUserPermissionsToDefault,
  setUserOverrides,
  setUserRoles,
  type Permission,
  type PermissionEffect,
  type Role,
  type User,
  type UserPermissionsResponse,
} from "@/lib/rbac";

type AdminUserTab = "roles" | "permissions";
type AccountFilter = "all" | "google" | "local";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<AdminUserTab>("roles");
  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());
  const [selectedPermissionKeys, setSelectedPermissionKeys] = useState<Set<string>>(new Set());
  const [defaultPermissionKeys, setDefaultPermissionKeys] = useState<Set<string>>(new Set());
  const [showDefaultHighlight, setShowDefaultHighlight] = useState(false);
  const [loading, setLoading] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [accountFilter, setAccountFilter] = useState<AccountFilter>("all");

  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) ?? null,
    [users, selectedUserId],
  );

  const filteredUsers = useMemo(() => {
    if (accountFilter === "all") return users;
    if (accountFilter === "google") return users.filter((user) => !!user.oidc_subject);
    return users.filter((user) => !user.oidc_subject);
  }, [accountFilter, users]);

  const loadBase = async () => {
    const [usersData, rolesData, permissionsData] = await Promise.all([
      listUsers(),
      listRoles(),
      listPermissions(),
    ]);
    setUsers(usersData);
    setRoles(rolesData);
    setPermissions(permissionsData);
    if (!selectedUserId && usersData.length > 0) {
      setSelectedUserId(usersData[0].id);
    }
  };

  const loadUserDetail = async (user: User) => {
    const permissionState = await getUserPermissions(user.id);
    hydrateUserState(user, permissionState);
  };

  const hydrateUserState = (user: User, permissionState: UserPermissionsResponse) => {
    setSelectedRoleIds(new Set(user.roles.map((role) => role.id)));
    setSelectedPermissionKeys(new Set(permissionState.effective_permissions));
    setDefaultPermissionKeys(new Set(permissionState.default_permissions));
  };

  useEffect(() => {
    loadBase().catch(() => toast.error("Failed to load users"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedUser) return;
    loadUserDetail(selectedUser).catch(() => toast.error("Failed to load user details"));
  }, [selectedUser]);

  useEffect(() => {
    if (filteredUsers.length === 0) {
      setSelectedUserId(null);
      return;
    }
    const stillVisible = filteredUsers.some((user) => user.id === selectedUserId);
    if (!stillVisible) {
      setSelectedUserId(filteredUsers[0].id);
    }
  }, [filteredUsers, selectedUserId]);

  const onCreateUser = async () => {
    if (!newUsername.trim() || !newEmail.trim() || !newPassword.trim()) {
      toast.error("Username, email, and password are required");
      return;
    }
    setLoading(true);
    try {
      const created = await createUser({
        username: newUsername.trim(),
        email: newEmail.trim(),
        password: newPassword,
      });
      await loadBase();
      setSelectedUserId(created.id);
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      toast.success("User created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  const onToggleRole = (roleId: string, checked: boolean) => {
    setSelectedRoleIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(roleId);
      } else {
        next.delete(roleId);
      }
      return next;
    });
  };

  const onSaveRoles = async () => {
    if (!selectedUserId) return;
    setLoading(true);
    try {
      await setUserRoles(selectedUserId, Array.from(selectedRoleIds));
      await loadBase();
      const refreshedUser = (await listUsers()).find((user) => user.id === selectedUserId);
      if (refreshedUser) {
        setUsers((prev) => prev.map((user) => (user.id === refreshedUser.id ? refreshedUser : user)));
        await loadUserDetail(refreshedUser);
      }
      toast.success("User roles updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save roles");
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

  const onSavePermissionOverrides = async () => {
    if (!selectedUserId) return;
    setLoading(true);
    try {
      const overrides: Array<{ permission_key: string; effect: PermissionEffect }> = [];
      for (const permission of permissions) {
        const key = permission.key;
        const isDefault = defaultPermissionKeys.has(key);
        const isSelected = selectedPermissionKeys.has(key);
        if (isSelected && !isDefault) {
          overrides.push({ permission_key: key, effect: "ALLOW" });
        }
        if (!isSelected && isDefault) {
          overrides.push({ permission_key: key, effect: "DENY" });
        }
      }
      await setUserOverrides(selectedUserId, overrides);
      const permissionState = await getUserPermissions(selectedUserId);
      setSelectedPermissionKeys(new Set(permissionState.effective_permissions));
      setDefaultPermissionKeys(new Set(permissionState.default_permissions));
      toast.success("Permission overrides saved");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save permission overrides");
    } finally {
      setLoading(false);
    }
  };

  const onResetToDefault = async () => {
    if (!selectedUserId) return;
    setLoading(true);
    try {
      const response = await resetUserPermissionsToDefault(selectedUserId);
      const defaults = new Set(response.permissions);
      setDefaultPermissionKeys(defaults);
      setSelectedPermissionKeys(defaults);
      toast.success("Permissions reset to role defaults");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to reset permissions");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-[300px_1fr]">
      <div className="space-y-4 rounded border p-4">
        <div className="text-sm font-semibold">Users</div>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={accountFilter === "all" ? "default" : "outline"}
            onClick={() => setAccountFilter("all")}
          >
            All
          </Button>
          <Button
            type="button"
            size="sm"
            variant={accountFilter === "google" ? "default" : "outline"}
            onClick={() => setAccountFilter("google")}
          >
            Google
          </Button>
          <Button
            type="button"
            size="sm"
            variant={accountFilter === "local" ? "default" : "outline"}
            onClick={() => setAccountFilter("local")}
          >
            Local
          </Button>
        </div>
        <div className="space-y-2 max-h-72 overflow-auto">
          {filteredUsers.map((user) => (
            <button
              key={user.id}
              type="button"
              onClick={() => setSelectedUserId(user.id)}
              className={`w-full rounded border px-3 py-2 text-left text-sm ${
                user.id === selectedUserId ? "border-blue-600 bg-blue-50" : "hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-medium">{user.username}</div>
                <span
                  className={`rounded px-2 py-0.5 text-[11px] font-semibold ${
                    user.oidc_subject ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {user.oidc_subject ? "Google-linked" : "Local"}
                </span>
              </div>
              <div className="text-xs text-gray-500">{user.email}</div>
            </button>
          ))}
          {filteredUsers.length === 0 && (
            <div className="rounded border border-dashed px-3 py-4 text-xs text-gray-500">
              No users match this account filter.
            </div>
          )}
        </div>

        <div className="space-y-2 border-t pt-4">
          <div className="text-sm font-semibold">Create user</div>
          <Input
            placeholder="Username"
            value={newUsername}
            onChange={(event) => setNewUsername(event.target.value)}
          />
          <Input placeholder="Email" value={newEmail} onChange={(event) => setNewEmail(event.target.value)} />
          <Input
            placeholder="Password"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
          <Button onClick={onCreateUser} disabled={loading} className="w-full">
            + Add user
          </Button>
        </div>
      </div>

      <div className="space-y-4 rounded border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">
            {selectedUser ? `User: ${selectedUser.username}` : "Select a user"}
          </div>
          {selectedUser && (
            <span
              className={`rounded px-2 py-1 text-xs font-semibold ${
                selectedUser.oidc_subject ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-700"
              }`}
            >
              {selectedUser.oidc_subject ? "Google-linked account" : "Local-only account"}
            </span>
          )}
          <div className="flex gap-2">
            <Button
              variant={activeTab === "roles" ? "default" : "outline"}
              onClick={() => setActiveTab("roles")}
              disabled={!selectedUser}
            >
              Roles
            </Button>
            <Button
              variant={activeTab === "permissions" ? "default" : "outline"}
              onClick={() => setActiveTab("permissions")}
              disabled={!selectedUser}
            >
              Permissions
            </Button>
          </div>
        </div>

        {activeTab === "roles" && (
          <div className="space-y-3">
            <div className="text-sm font-semibold">Role assignments</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((role) => (
                <label key={role.id} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
                  <Checkbox
                    checked={selectedRoleIds.has(role.id)}
                    disabled={!selectedUser || loading}
                    onCheckedChange={(checked) => onToggleRole(role.id, checked === true)}
                  />
                  <span>{role.name}</span>
                </label>
              ))}
            </div>
            <Button onClick={onSaveRoles} disabled={!selectedUser || loading}>
              Save roles
            </Button>
          </div>
        )}

        {activeTab === "permissions" && (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                onClick={() => setShowDefaultHighlight((value) => !value)}
                disabled={!selectedUser}
              >
                {showDefaultHighlight ? "Hide default highlight" : "View default"}
              </Button>
              <Button variant="outline" onClick={onResetToDefault} disabled={!selectedUser || loading}>
                Reset to default
              </Button>
              <Button onClick={onSavePermissionOverrides} disabled={!selectedUser || loading}>
                Save overrides
              </Button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {permissions.map((permission) => {
                const isDefault = defaultPermissionKeys.has(permission.key);
                const highlighted = showDefaultHighlight && isDefault;
                return (
                  <label
                    key={permission.id}
                    className={`flex items-center gap-2 rounded border px-3 py-2 text-sm ${
                      highlighted ? "border-blue-500 bg-blue-50" : ""
                    }`}
                  >
                    <Checkbox
                      checked={selectedPermissionKeys.has(permission.key)}
                      disabled={!selectedUser || loading}
                      onCheckedChange={(checked) => onTogglePermission(permission.key, checked === true)}
                    />
                    <span>{permission.key}</span>
                  </label>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
