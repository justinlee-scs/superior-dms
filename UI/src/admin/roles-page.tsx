import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Clock3,
  Copy,
  Eye,
  GitBranch,
  Lock,
  Plus,
  RotateCcw,
  Shield,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/app/components/ui/button";
import { Checkbox } from "@/app/components/ui/checkbox";

import {
  activateUser,
  addManagedRole,
  addManagedUser,
  addUserManagedRole,
  addUserManagedUser,
  copyRolePermissions,
  createRole,
  createUser,
  deactivateUser,
  getRole,
  getUserPermissions,
  listManagedRoles,
  listManagedUsers,
  listPermissions,
  listRoles,
  listUserManagedRoles,
  listUserManagedUsers,
  listUsers,
  removeManagedRole,
  removeManagedUser,
  removeUserManagedRole,
  removeUserManagedUser,
  resetUserPermissionsToDefault,
  setRolePermissions,
  updateRole,
  setUserOverrides,
  setUserRoles,
  type Permission,
  type PermissionEffect,
  type Role,
  type User,
  type UserPermissionsResponse,
} from "@/lib/rbac";
import { getRetrainSchedule, updateRetrainSchedule } from "@/lib/dms";

type AdminSection = "roles" | "users" | "hierarchy" | "training";
type UserTab = "roles" | "permissions";
type HierarchyManagerType = "role" | "user";

const PERMISSION_LABELS: Record<string, string> = {
  "document.read": "View Documents",
  "document.upload": "Create Documents",
  "document.update": "Edit Documents",
  "document.delete": "Delete Documents",
  "document.download": "Download Documents",
  "document.preview": "Preview Documents",
  "document.due_payments": "View Upcoming Payments",
  "workflow.advance": "View Workflows",
  "workflow.assign": "Edit Workflows",
  "admin.users": "Manage Users",
  "admin.roles": "Manage Roles",
  "admin.training": "Manage Training",
  "tags.read": "View Tags",
  "tags.edit": "Edit Tags",
};

const PERMISSION_DESCRIPTIONS: Record<string, string> = {
  "document.read": "Can view documents",
  "document.upload": "Can upload new documents",
  "document.update": "Can edit document metadata",
  "document.delete": "Can delete documents",
  "document.download": "Can download documents",
  "document.preview": "Can preview documents",
  "document.due_payments": "Can view upcoming due payments",
  "workflow.advance": "Can view workflow status",
  "workflow.assign": "Can modify workflows",
  "admin.users": "Can create and update users",
  "admin.roles": "Can create and update roles",
  "admin.training": "Can configure nightly retraining schedule",
  "tags.read": "Can view document tags",
  "tags.edit": "Can add, remove, and replace document tags",
};

function permissionGroup(permissionKey: string): string {
  if (permissionKey.startsWith("document_version.")) return "Versioning";
  if (permissionKey.startsWith("document.")) return "Documents";
  if (permissionKey.startsWith("tags.")) return "Tags";
  if (permissionKey.startsWith("workflow.")) return "Workflows";
  if (permissionKey.startsWith("admin.")) return "Administration";
  return "Other";
}

function titleCaseFromKey(permissionKey: string): string {
  const base = permissionKey.split(".").pop() ?? permissionKey;
  return base.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function RolesPage({
  darkMode = false,
  onBackToDocuments,
}: {
  darkMode?: boolean;
  onBackToDocuments?: () => void;
}) {
  const [section, setSection] = useState<AdminSection>("roles");
  const [loading, setLoading] = useState(false);

  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  const [rolePermissionCounts, setRolePermissionCounts] = useState<Record<string, number | null>>({});
  const [userPermissionCounts, setUserPermissionCounts] = useState<Record<string, number | null>>({});

  const [managedRoleMap, setManagedRoleMap] = useState<Record<string, Role[]>>({});
  const [managedUserMap, setManagedUserMap] = useState<Record<string, User[]>>({});
  const [managedByMap, setManagedByMap] = useState<Record<string, Role[]>>({});
  const [managedByUserMap, setManagedByUserMap] = useState<Record<string, User[]>>({});

  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [hierarchyManagerType, setHierarchyManagerType] = useState<HierarchyManagerType>("role");
  const [hierarchyManagerRoleId, setHierarchyManagerRoleId] = useState<string | null>(null);
  const [hierarchyManagerUserId, setHierarchyManagerUserId] = useState<string | null>(null);
  const [selectedPermissionKeys, setSelectedPermissionKeys] = useState<Set<string>>(new Set());
  const [managedRoleIds, setManagedRoleIds] = useState<Set<string>>(new Set());
  const [managedUserIds, setManagedUserIds] = useState<Set<string>>(new Set());
  const [managedRoleIdsByUser, setManagedRoleIdsByUser] = useState<Set<string>>(new Set());
  const [managedUserIdsByUser, setManagedUserIdsByUser] = useState<Set<string>>(new Set());
  const [expandedManagedRoles, setExpandedManagedRoles] = useState<Set<string>>(new Set());
  const [expandedManagedUsers, setExpandedManagedUsers] = useState<Set<string>>(new Set());
  const [copySourceRoleId, setCopySourceRoleId] = useState<string>("");

  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [userTab, setUserTab] = useState<UserTab>("roles");
  const [selectedUserRoleIds, setSelectedUserRoleIds] = useState<Set<string>>(new Set());
  const [selectedUserPermissionKeys, setSelectedUserPermissionKeys] = useState<Set<string>>(new Set());
  const [defaultUserPermissionKeys, setDefaultUserPermissionKeys] = useState<Set<string>>(new Set());
  const [showDefaultHighlight, setShowDefaultHighlight] = useState(false);
  const [retrainEnabled, setRetrainEnabled] = useState(true);
  const [retrainTimezone, setRetrainTimezone] = useState("America/Los_Angeles");
  const [retrainHour, setRetrainHour] = useState(3);
  const [retrainMinute, setRetrainMinute] = useState(0);

  const selectedRole = useMemo(
    () => roles.find((role) => role.id === selectedRoleId) ?? null,
    [roles, selectedRoleId],
  );

  const selectedUser = useMemo(
    () => users.find((user) => user.id === selectedUserId) ?? null,
    [users, selectedUserId],
  );
  const hierarchyManagerRole = useMemo(
    () => roles.find((role) => role.id === hierarchyManagerRoleId) ?? null,
    [roles, hierarchyManagerRoleId],
  );
  const hierarchyManagerUser = useMemo(
    () => users.find((user) => user.id === hierarchyManagerUserId) ?? null,
    [users, hierarchyManagerUserId],
  );

  const groupedPermissions = useMemo(() => {
    const grouped: Record<string, Permission[]> = {};
    for (const permission of permissions) {
      const group = permissionGroup(permission.key);
      if (!grouped[group]) grouped[group] = [];
      grouped[group].push(permission);
    }
    return grouped;
  }, [permissions]);

  const loadRoleDetails = async (roleId: string) => {
    const [roleWithPermissions, managedRoles, managedUsers] = await Promise.all([
      getRole(roleId),
      listManagedRoles(roleId),
      listManagedUsers(roleId),
    ]);
    setSelectedPermissionKeys(new Set(roleWithPermissions.permissions.map((permission) => permission.key)));
    setManagedRoleIds(new Set(managedRoles.map((role) => role.id)));
    setManagedUserIds(new Set(managedUsers.map((user) => user.id)));
  };

  const loadUserManagerDetails = async (userId: string) => {
    const [managedRoles, managedUsers] = await Promise.all([
      listUserManagedRoles(userId),
      listUserManagedUsers(userId),
    ]);
    setManagedRoleIdsByUser(new Set(managedRoles.map((role) => role.id)));
    setManagedUserIdsByUser(new Set(managedUsers.map((user) => user.id)));
  };

  const hydrateUserState = (user: User, permissionState: UserPermissionsResponse) => {
    setSelectedUserRoleIds(new Set(user.roles.map((role) => role.id)));
    setSelectedUserPermissionKeys(new Set(permissionState.effective_permissions));
    setDefaultUserPermissionKeys(new Set(permissionState.default_permissions));
  };

  const loadUserDetails = async (user: User) => {
    const state = await getUserPermissions(user.id);
    hydrateUserState(user, state);
  };

  const loadHierarchyMaps = async (rolesData: Role[], usersData: User[]) => {
    const [roleEntries, userEntries, userManagedRoleEntries] = await Promise.all([
      Promise.all(rolesData.map(async (role) => [role.id, await listManagedRoles(role.id)] as const)),
      Promise.all(rolesData.map(async (role) => [role.id, await listManagedUsers(role.id)] as const)),
      Promise.all(usersData.map(async (user) => [user.id, await listUserManagedRoles(user.id)] as const)),
    ]);
    const canManageRoles: Record<string, Role[]> = Object.fromEntries(roleEntries);
    const canManageUsers: Record<string, User[]> = Object.fromEntries(userEntries);
    const managedBy: Record<string, Role[]> = {};
    const managedByUsers: Record<string, User[]> = {};

    for (const role of rolesData) managedBy[role.id] = [];
    for (const role of rolesData) managedByUsers[role.id] = [];

    for (const [managerId, managedRoles] of roleEntries) {
      const manager = rolesData.find((role) => role.id === managerId);
      if (!manager) continue;
      for (const managedRole of managedRoles) {
        if (!managedBy[managedRole.id]) managedBy[managedRole.id] = [];
        managedBy[managedRole.id].push(manager);
      }
    }

    for (const [managerUserId, managedRoles] of userManagedRoleEntries) {
      const managerUser = usersData.find((user) => user.id === managerUserId);
      if (!managerUser) continue;
      for (const managedRole of managedRoles) {
        if (!managedByUsers[managedRole.id]) managedByUsers[managedRole.id] = [];
        managedByUsers[managedRole.id].push(managerUser);
      }
    }

    setManagedRoleMap(canManageRoles);
    setManagedUserMap(canManageUsers);
    setManagedByMap(managedBy);
    setManagedByUserMap(managedByUsers);
  };

  const loadBase = async () => {
    const [rolesData, permissionsData, usersData] = await Promise.all([
      listRoles(),
      listPermissions(),
      listUsers(),
    ]);

    setRoles(rolesData);
    setPermissions(permissionsData);
    setUsers(usersData);

    if (!selectedRoleId && rolesData.length > 0) {
      setSelectedRoleId(rolesData[0].id);
    }
    if (!selectedUserId && usersData.length > 0) {
      setSelectedUserId(usersData[0].id);
    }
    if (!hierarchyManagerRoleId && rolesData.length > 0) {
      setHierarchyManagerRoleId(rolesData[0].id);
    }
    if (!hierarchyManagerUserId && usersData.length > 0) {
      setHierarchyManagerUserId(usersData[0].id);
    }

    try {
      await loadHierarchyMaps(rolesData, usersData);
    } catch (error) {
      console.warn("Failed to load hierarchy maps", error);
    }

    const roleCountsEntries = await Promise.allSettled(
      rolesData.map(async (role) => {
        const details = await getRole(role.id);
        return [role.id, details.permissions.length] as const;
      }),
    );
    const roleCounts = roleCountsEntries.map((entry, index) => {
      if (entry.status === "fulfilled") return entry.value;
      return [rolesData[index].id, null] as const;
    });
    setRolePermissionCounts(Object.fromEntries(roleCounts));

    const userCountsEntries = await Promise.allSettled(
      usersData.map(async (user) => {
        const details = await getUserPermissions(user.id);
        return [user.id, details.effective_permissions.length] as const;
      }),
    );
    const userCounts = userCountsEntries.map((entry, index) => {
      if (entry.status === "fulfilled") return entry.value;
      return [usersData[index].id, null] as const;
    });
    setUserPermissionCounts(Object.fromEntries(userCounts));

    try {
      const schedule = await getRetrainSchedule();
      setRetrainEnabled(schedule.enabled);
      setRetrainTimezone(schedule.timezone);
      setRetrainHour(schedule.hour);
      setRetrainMinute(schedule.minute);
    } catch (error) {
      console.warn("Failed to load retrain schedule", error);
    }
  };

  useEffect(() => {
    loadBase().catch(() => toast.error("Failed to load admin data"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRoleId) return;
    loadRoleDetails(selectedRoleId).catch(() => toast.error("Failed to load role details"));
  }, [selectedRoleId]);

  useEffect(() => {
    if (!hierarchyManagerRoleId) return;
    if (hierarchyManagerType !== "role") return;
    loadRoleDetails(hierarchyManagerRoleId).catch(() => toast.error("Failed to load role manager details"));
  }, [hierarchyManagerRoleId, hierarchyManagerType]);

  useEffect(() => {
    if (!hierarchyManagerUserId) return;
    if (hierarchyManagerType !== "user") return;
    loadUserManagerDetails(hierarchyManagerUserId).catch(() => toast.error("Failed to load user manager details"));
  }, [hierarchyManagerUserId, hierarchyManagerType]);

  useEffect(() => {
    if (!selectedUser) return;
    loadUserDetails(selectedUser).catch(() => toast.error("Failed to load user details"));
  }, [selectedUser]);

  const onCreateRole = async () => {
    const roleName = window.prompt("New role name");
    if (!roleName?.trim()) return;
    const description = window.prompt("Role description (optional)") ?? "";

    setLoading(true);
    try {
      const role = await createRole({
        name: roleName.trim(),
        description: description.trim() || undefined,
      });
      await loadBase();
      setSelectedRoleId(role.id);
      toast.success("Role created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create role");
    } finally {
      setLoading(false);
    }
  };

  const onEditRole = async () => {
    if (!selectedRole) return;
    const roleName = window.prompt("Role name", selectedRole.name);
    if (!roleName) return;
    const description = window.prompt("Role description", selectedRole.description ?? "");
    if (description === null) return;

    setLoading(true);
    try {
      await updateRole(selectedRole.id, {
        name: roleName.trim(),
        description,
      });
      await loadBase();
      await loadRoleDetails(selectedRole.id);
      toast.success("Role updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update role");
    } finally {
      setLoading(false);
    }
  };

  const onTogglePermission = async (permissionKey: string, checked: boolean) => {
    if (!selectedRoleId) return;

    const previous = new Set(selectedPermissionKeys);
    const next = new Set(selectedPermissionKeys);
    if (checked) next.add(permissionKey);
    else next.delete(permissionKey);

    setSelectedPermissionKeys(next);

    try {
      await setRolePermissions(selectedRoleId, Array.from(next));
      setRolePermissionCounts((prev) => ({ ...prev, [selectedRoleId]: next.size }));
    } catch (error) {
      setSelectedPermissionKeys(previous);
      toast.error(error instanceof Error ? error.message : "Failed to update role permissions");
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
      setCopySourceRoleId("");
      toast.success("Permissions copied");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to copy permissions");
    } finally {
      setLoading(false);
    }
  };

  const onToggleManagedRole = async (managedRoleId: string, checked: boolean) => {
    if (hierarchyManagerType === "role" && !hierarchyManagerRoleId) return;
    if (hierarchyManagerType === "user" && !hierarchyManagerUserId) return;
    setLoading(true);
    try {
      if (hierarchyManagerType === "role" && hierarchyManagerRoleId) {
        if (checked) await addManagedRole(hierarchyManagerRoleId, managedRoleId);
        else await removeManagedRole(hierarchyManagerRoleId, managedRoleId);
        await loadRoleDetails(hierarchyManagerRoleId);
      } else if (hierarchyManagerType === "user" && hierarchyManagerUserId) {
        if (checked) await addUserManagedRole(hierarchyManagerUserId, managedRoleId);
        else await removeUserManagedRole(hierarchyManagerUserId, managedRoleId);
        await loadUserManagerDetails(hierarchyManagerUserId);
      }

      await loadHierarchyMaps(roles, users);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update role hierarchy");
    } finally {
      setLoading(false);
    }
  };

  const onToggleManagedUser = async (managedUserId: string, checked: boolean) => {
    if (hierarchyManagerType === "role" && !hierarchyManagerRoleId) return;
    if (hierarchyManagerType === "user" && !hierarchyManagerUserId) return;
    setLoading(true);
    try {
      if (hierarchyManagerType === "role" && hierarchyManagerRoleId) {
        if (checked) await addManagedUser(hierarchyManagerRoleId, managedUserId);
        else await removeManagedUser(hierarchyManagerRoleId, managedUserId);
        await loadRoleDetails(hierarchyManagerRoleId);
      } else if (hierarchyManagerType === "user" && hierarchyManagerUserId) {
        if (checked) await addUserManagedUser(hierarchyManagerUserId, managedUserId);
        else await removeUserManagedUser(hierarchyManagerUserId, managedUserId);
        await loadUserManagerDetails(hierarchyManagerUserId);
      }

      await loadHierarchyMaps(roles, users);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update role user management");
    } finally {
      setLoading(false);
    }
  };

  const onCreateUser = async () => {
    const username = window.prompt("Username");
    if (!username?.trim()) return;
    const email = window.prompt("Email");
    if (!email?.trim()) return;
    const password = window.prompt("Password");
    if (!password?.trim()) return;

    setLoading(true);
    try {
      const created = await createUser({
        username: username.trim(),
        email: email.trim(),
        password: password.trim(),
      });
      await loadBase();
      setSelectedUserId(created.id);
      toast.success("User created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  const onToggleUserActive = async () => {
    if (!selectedUser) return;
    setLoading(true);
    try {
      const updatedUser = selectedUser.is_active
        ? await deactivateUser(selectedUser.id)
        : await activateUser(selectedUser.id);
      setUsers((prev) => prev.map((user) => (user.id === updatedUser.id ? updatedUser : user)));
      toast.success(updatedUser.is_active ? "User activated" : "User deactivated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update user status");
    } finally {
      setLoading(false);
    }
  };

  const onToggleUserRole = async (roleId: string, checked: boolean) => {
    if (!selectedUserId || !selectedUser) return;

    const previous = new Set(selectedUserRoleIds);
    const next = new Set(selectedUserRoleIds);
    if (checked) next.add(roleId);
    else next.delete(roleId);

    setSelectedUserRoleIds(next);

    try {
      await setUserRoles(selectedUserId, Array.from(next));
      const refreshedUsers = await listUsers();
      setUsers(refreshedUsers);
      const refreshedUser = refreshedUsers.find((user) => user.id === selectedUserId);
      if (refreshedUser) {
        const permissionState = await getUserPermissions(selectedUserId);
        hydrateUserState(refreshedUser, permissionState);
        setUserPermissionCounts((prev) => ({
          ...prev,
          [selectedUserId]: permissionState.effective_permissions.length,
        }));
      }
    } catch (error) {
      setSelectedUserRoleIds(previous);
      toast.error(error instanceof Error ? error.message : "Failed to update user roles");
    }
  };

  const persistUserOverrides = async (nextPermissionKeys: Set<string>) => {
    if (!selectedUserId) return;

    const overrides: Array<{ permission_key: string; effect: PermissionEffect }> = [];
    for (const permission of permissions) {
      const key = permission.key;
      const fromRoles = defaultUserPermissionKeys.has(key);
      const selected = nextPermissionKeys.has(key);
      if (selected && !fromRoles) overrides.push({ permission_key: key, effect: "ALLOW" });
      if (!selected && fromRoles) overrides.push({ permission_key: key, effect: "DENY" });
    }

    await setUserOverrides(selectedUserId, overrides);
  };

  const onToggleUserPermission = async (permissionKey: string, checked: boolean) => {
    if (!selectedUserId) return;

    const previous = new Set(selectedUserPermissionKeys);
    const next = new Set(selectedUserPermissionKeys);
    if (checked) next.add(permissionKey);
    else next.delete(permissionKey);
    setSelectedUserPermissionKeys(next);

    try {
      await persistUserOverrides(next);
      setUserPermissionCounts((prev) => ({ ...prev, [selectedUserId]: next.size }));
    } catch (error) {
      setSelectedUserPermissionKeys(previous);
      toast.error(error instanceof Error ? error.message : "Failed to update permissions");
    }
  };

  const onResetUserPermissions = async () => {
    if (!selectedUserId) return;
    setLoading(true);
    try {
      const response = await resetUserPermissionsToDefault(selectedUserId);
      const defaults = new Set(response.permissions);
      setDefaultUserPermissionKeys(defaults);
      setSelectedUserPermissionKeys(defaults);
      setUserPermissionCounts((prev) => ({ ...prev, [selectedUserId]: defaults.size }));
      toast.success("Permissions reset to default");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to reset permissions");
    } finally {
      setLoading(false);
    }
  };

  const activeManagedRoleIds = hierarchyManagerType === "role" ? managedRoleIds : managedRoleIdsByUser;
  const activeManagedUserIds = hierarchyManagerType === "role" ? managedUserIds : managedUserIdsByUser;
  const hierarchyManagerLabel =
    hierarchyManagerType === "role" ? hierarchyManagerRole?.name : hierarchyManagerUser?.username;

  const toggleExpandedManagedRoles = (roleId: string) => {
    setExpandedManagedRoles((prev) => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const toggleExpandedManagedUsers = (roleId: string) => {
    setExpandedManagedUsers((prev) => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const onSaveRetrainSchedule = async () => {
    setLoading(true);
    try {
      await updateRetrainSchedule({
        enabled: retrainEnabled,
        timezone: retrainTimezone.trim(),
        hour: retrainHour,
        minute: retrainMinute,
      });
      toast.success("Nightly retrain schedule updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update retrain schedule");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`mt-6 overflow-hidden rounded-xl border ${
        darkMode ? "border-gray-700 bg-gray-900 text-gray-100" : "border-gray-200 bg-[#f3f4f6]"
      }`}
    >
      <div
        className={`grid min-h-[72vh] ${
          section === "hierarchy" || section === "training"
            ? "grid-cols-[230px_1fr]"
            : "grid-cols-[230px_320px_1fr]"
        }`}
      >
        <aside
          className={`border-r px-4 py-4 ${
            darkMode ? "border-gray-700 bg-gray-900" : "border-gray-200 bg-[#f3f4f6]"
          }`}
        >
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-3 text-base font-semibold">
              <Shield className="h-7 w-7 text-blue-600" />
              <span className="text-2xl">Admin Panel</span>
            </div>
          </div>

          <Button
            variant="outline"
            className={`mb-5 w-full justify-start rounded-xl text-sm ${
              darkMode ? "border-gray-600 bg-gray-800 text-gray-100 hover:bg-gray-700" : "border-gray-300 bg-transparent"
            }`}
            onClick={() => onBackToDocuments?.()}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Documents
          </Button>

          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setSection("roles")}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold ${
                section === "roles"
                  ? "bg-[#020825] text-white"
                  : darkMode
                    ? "text-gray-100 hover:bg-gray-800"
                    : "text-black hover:bg-gray-200"
              }`}
            >
              <Shield className="h-5 w-5" />
              Roles
            </button>
            <button
              type="button"
              onClick={() => setSection("users")}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold ${
                section === "users"
                  ? "bg-[#020825] text-white"
                  : darkMode
                    ? "text-gray-100 hover:bg-gray-800"
                    : "text-black hover:bg-gray-200"
              }`}
            >
              <Users className="h-5 w-5" />
              Users
            </button>
            <button
              type="button"
              onClick={() => setSection("hierarchy")}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold ${
                section === "hierarchy"
                  ? "bg-[#020825] text-white"
                  : darkMode
                    ? "text-gray-100 hover:bg-gray-800"
                    : "text-black hover:bg-gray-200"
              }`}
            >
              <GitBranch className="h-5 w-5" />
              Hierarchy
            </button>
            <button
              type="button"
              onClick={() => setSection("training")}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-semibold ${
                section === "training"
                  ? "bg-[#020825] text-white"
                  : darkMode
                    ? "text-gray-100 hover:bg-gray-800"
                    : "text-black hover:bg-gray-200"
              }`}
            >
              <Clock3 className="h-5 w-5" />
              Training
            </button>
          </div>
        </aside>

        {section === "roles" && (
          <section className={`border-r ${darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200 bg-[#f7f7f8]"}`}>
            <div className={`flex items-center justify-between border-b px-3 py-2 ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
              <div>
                <div className="text-xl font-semibold">Roles</div>
                <div className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>{roles.length} role(s)</div>
              </div>
              <Button className="rounded-xl bg-[#020825] px-4 text-sm" onClick={onCreateRole} disabled={loading}>
                <Plus className="mr-1 h-4 w-4" />
                New
              </Button>
            </div>

            <div className="max-h-[calc(72vh-80px)] space-y-2 overflow-auto p-3">
              {roles.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => setSelectedRoleId(role.id)}
                  className={`w-full rounded-xl border px-3 py-2 text-left ${
                    role.id === selectedRoleId
                      ? "border-blue-300 bg-blue-50/40"
                      : darkMode
                        ? "border-transparent hover:bg-gray-700"
                        : "border-transparent hover:bg-gray-100"
                  }`}
                >
                  <div className="text-lg font-semibold">{role.name}</div>
                  <div className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>{role.description || "No description"}</div>
                  <div className={`mt-1 text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                    {rolePermissionCounts[role.id] ?? "—"} permission(s)
                  </div>
                  <div className="mt-1 inline-flex items-center rounded-md bg-purple-100 px-2 py-0.5 text-xs text-purple-700">
                    <Lock className="mr-1 h-3 w-3" />
                    clearance:{role.name.toLowerCase()}
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        {section === "users" && (
          <section className={`border-r ${darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200 bg-[#f7f7f8]"}`}>
            <div className={`flex items-center justify-between border-b px-3 py-2 ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
              <div>
                <div className="text-xl font-semibold">Users</div>
                <div className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>{users.length} user(s)</div>
              </div>
              <Button className="rounded-xl bg-[#020825] px-4 text-sm" onClick={onCreateUser} disabled={loading}>
                <Plus className="mr-1 h-4 w-4" />
                New
              </Button>
            </div>

            <div className="max-h-[calc(72vh-80px)] space-y-2 overflow-auto p-3">
              {users.map((user) => (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => setSelectedUserId(user.id)}
                  className={`w-full rounded-xl border px-3 py-2 text-left ${
                    user.id === selectedUserId
                      ? "border-blue-300 bg-blue-50/40"
                      : darkMode
                        ? "border-transparent hover:bg-gray-700"
                        : "border-transparent hover:bg-gray-100"
                  }`}
                >
                  <div className="text-lg font-semibold">{user.username}</div>
                  <div className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>{user.email}</div>
                  <div className="mt-2">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                        user.is_active
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <div className={`mt-1 text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                    {user.roles.length} role(s), {userPermissionCounts[user.id] ?? "—"} permission(s)
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        <main className={darkMode ? "bg-gray-900 text-gray-100" : "bg-white"}>
          {section === "roles" && selectedRole && (
            <>
              <div className={`flex items-start justify-between border-b px-3 py-2 ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
                <div>
                  <div className="text-2xl font-semibold">{selectedRole.name}</div>
                  <div className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                    {selectedRole.description || "No description provided"}
                  </div>
                  <div className={`mt-2 flex items-center gap-2 text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                    <span>
                      {selectedPermissionKeys.size} of {permissions.length} permissions assigned
                    </span>
                    <span className="inline-flex items-center rounded-md bg-purple-100 px-2 py-0.5 text-xs text-purple-700">
                      <Lock className="mr-1 h-3 w-3" />
                      clearance:{selectedRole.name.toLowerCase()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    className="h-10 rounded-xl border border-gray-300 px-3 text-sm"
                    value={copySourceRoleId}
                    onChange={(event) => setCopySourceRoleId(event.target.value)}
                    disabled={loading}
                  >
                    <option value="">Select source role</option>
                    {roles
                      .filter((role) => role.id !== selectedRoleId)
                      .map((role) => (
                        <option key={role.id} value={role.id}>
                          {role.name}
                        </option>
                      ))}
                  </select>
                  <Button
                    variant="outline"
                    className="rounded-xl"
                    onClick={onCopyFromRole}
                    disabled={!copySourceRoleId || loading}
                  >
                    <Copy className="mr-2 h-4 w-4" />
                    Copy from Other Role
                  </Button>
                  <Button variant="outline" className="rounded-xl" onClick={onEditRole} disabled={loading}>
                    Edit Role
                  </Button>
                </div>
              </div>

              <div className="max-h-[calc(72vh-120px)] overflow-auto px-3 py-2">
                {Object.entries(groupedPermissions).map(([group, groupPermissions]) => (
                  <div key={group} className="mb-8">
                    <h3 className="mb-3 text-lg font-semibold">{group}</h3>
                    <div className="space-y-4">
                      {groupPermissions.map((permission) => (
                        <label key={permission.id} className="flex items-start gap-3">
                          <Checkbox
                            className="mt-1"
                            checked={selectedPermissionKeys.has(permission.key)}
                            onCheckedChange={(checked) =>
                              void onTogglePermission(permission.key, checked === true)
                            }
                          />
                          <div>
                            <div className="text-sm font-semibold">
                              {PERMISSION_LABELS[permission.key] ?? titleCaseFromKey(permission.key)}
                            </div>
                            <div className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                              {PERMISSION_DESCRIPTIONS[permission.key] ??
                                permission.description ??
                                permission.key}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {section === "users" && selectedUser && (
            <>
              <div className={`border-b px-3 py-2 ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-2xl font-semibold">{selectedUser.username}</div>
                    <div className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>{selectedUser.email}</div>
                    <div className="mt-2">
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                          selectedUser.is_active
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-amber-100 text-amber-700"
                        }`}
                      >
                        {selectedUser.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>
                  <Button
                    variant={selectedUser.is_active ? "outline" : "default"}
                    className="rounded-xl"
                    onClick={onToggleUserActive}
                    disabled={loading}
                  >
                    {selectedUser.is_active ? "Deactivate user" : "Activate user"}
                  </Button>
                </div>
              </div>

              <div className={`border-b px-6 ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
                <div className="flex gap-8">
                  <button
                    type="button"
                    onClick={() => setUserTab("roles")}
                    className={`border-b-2 py-3 text-base font-semibold ${
                      userTab === "roles"
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-gray-700"
                    }`}
                  >
                    Roles
                  </button>
                  <button
                    type="button"
                    onClick={() => setUserTab("permissions")}
                    className={`border-b-2 py-3 text-base font-semibold ${
                      userTab === "permissions"
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-gray-700"
                    }`}
                  >
                    Permissions
                  </button>
                </div>
              </div>

              <div className="max-h-[calc(72vh-180px)] overflow-auto px-3 py-2">
                {userTab === "roles" && (
                  <div className="space-y-4">
                    {roles.map((role) => (
                      <label key={role.id} className="flex items-center gap-3">
                        <Checkbox
                          checked={selectedUserRoleIds.has(role.id)}
                          onCheckedChange={(checked) =>
                            void onToggleUserRole(role.id, checked === true)
                          }
                        />
                        <div>
                          <div className="text-base font-semibold">{role.name}</div>
                          <div className="text-sm text-gray-500">{role.description || "No description"}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                )}

                {userTab === "permissions" && (
                  <div>
                    <div className="mb-5 flex items-center justify-between">
                      <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                        Customize permissions for this user. Changes override role defaults.
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          className="rounded-xl"
                          onClick={() => setShowDefaultHighlight((value) => !value)}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View Default
                        </Button>
                        <Button
                          variant="outline"
                          className="rounded-xl"
                          onClick={onResetUserPermissions}
                          disabled={loading}
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Reset to Default
                        </Button>
                      </div>
                    </div>

                    {Object.entries(groupedPermissions).map(([group, groupPermissions]) => (
                      <div key={group} className="mb-8">
                        <h3 className="mb-3 text-lg font-semibold">{group}</h3>
                        <div className="space-y-4">
                          {groupPermissions.map((permission) => {
                            const fromRoles = defaultUserPermissionKeys.has(permission.key);
                            const highlighted = showDefaultHighlight && fromRoles;
                            return (
                              <label
                                key={permission.id}
                                className={`flex items-start gap-3 rounded-lg px-2 py-1 ${
                                  highlighted ? "bg-blue-50" : ""
                                }`}
                              >
                                <Checkbox
                                  className="mt-1"
                                  checked={selectedUserPermissionKeys.has(permission.key)}
                                  onCheckedChange={(checked) =>
                                    void onToggleUserPermission(permission.key, checked === true)
                                  }
                                />
                                <div>
                                  <div className="text-sm font-semibold">
                                    {PERMISSION_LABELS[permission.key] ?? titleCaseFromKey(permission.key)}
                                    {fromRoles && (
                                      <span className="ml-2 text-sm font-normal text-blue-600">(From roles)</span>
                                    )}
                                  </div>
                                  <div className={`text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                    {PERMISSION_DESCRIPTIONS[permission.key] ??
                                      permission.description ??
                                      permission.key}
                                  </div>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {section === "hierarchy" && (
            <div className="px-3 py-2">
              <h2 className="text-2xl font-semibold">Role Hierarchy</h2>
              <p className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                Visual representation of which roles can manage other roles and users. Management does not grant extra permissions.
              </p>

              <div
                className={`mt-4 rounded-xl border p-4 ${
                  darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200 bg-[#f8f8f9]"
                }`}
              >
                <div className="mb-3 text-lg font-semibold">Edit Hierarchy</div>
                <div className="mb-4 grid gap-3">
                  <div className="grid gap-2">
                    <label className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                      Manager Type
                    </label>
                    <div className="flex gap-2">
                      <Button
                        variant={hierarchyManagerType === "role" ? "default" : "outline"}
                        onClick={() => setHierarchyManagerType("role")}
                        disabled={loading}
                      >
                        Role
                      </Button>
                      <Button
                        variant={hierarchyManagerType === "user" ? "default" : "outline"}
                        onClick={() => setHierarchyManagerType("user")}
                        disabled={loading}
                      >
                        User
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <label className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                      {hierarchyManagerType === "role" ? "Manager Role" : "Manager User"}
                    </label>
                    {hierarchyManagerType === "role" ? (
                      <select
                        className="h-10 rounded-xl border border-gray-300 bg-white px-3 text-sm text-black"
                        value={hierarchyManagerRoleId ?? ""}
                        onChange={(event) => setHierarchyManagerRoleId(event.target.value || null)}
                        disabled={loading || roles.length === 0}
                      >
                        {roles.map((role) => (
                          <option key={role.id} value={role.id}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <select
                        className="h-10 rounded-xl border border-gray-300 bg-white px-3 text-sm text-black"
                        value={hierarchyManagerUserId ?? ""}
                        onChange={(event) => setHierarchyManagerUserId(event.target.value || null)}
                        disabled={loading || users.length === 0}
                      >
                        {users.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.username} ({user.email})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>

                {hierarchyManagerType === "role" && !hierarchyManagerRole && (
                  <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                    Select a role to edit which roles it can manage.
                  </div>
                )}

                {hierarchyManagerType === "user" && !hierarchyManagerUser && (
                  <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                    Select a user to edit which roles and users they can manage.
                  </div>
                )}

                {hierarchyManagerLabel && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                        Roles managed by <span className="font-semibold">{hierarchyManagerLabel}</span>:
                      </div>
                      {roles
                        .filter((role) =>
                          hierarchyManagerType === "role" && hierarchyManagerRole
                            ? role.id !== hierarchyManagerRole.id
                            : true,
                        )
                        .map((role) => (
                          <label key={role.id} className="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
                            <div>
                              <div className="text-sm font-semibold">{role.name}</div>
                              <div className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                {role.description || "No description"}
                              </div>
                            </div>
                            <Checkbox
                              checked={activeManagedRoleIds.has(role.id)}
                              onCheckedChange={(checked) =>
                                void onToggleManagedRole(role.id, checked === true)
                              }
                            />
                          </label>
                        ))}
                    </div>

                    <div className="space-y-2">
                      <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                        Users managed by <span className="font-semibold">{hierarchyManagerLabel}</span>:
                      </div>
                      {users
                        .filter((user) =>
                          hierarchyManagerType === "user" && hierarchyManagerUser
                            ? user.id !== hierarchyManagerUser.id
                            : true,
                        )
                        .map((user) => (
                          <label key={user.id} className="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
                            <div>
                              <div className="text-sm font-semibold">{user.username}</div>
                              <div className={`text-xs ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                {user.email}
                              </div>
                            </div>
                            <Checkbox
                              checked={activeManagedUserIds.has(user.id)}
                              onCheckedChange={(checked) =>
                                void onToggleManagedUser(user.id, checked === true)
                              }
                            />
                          </label>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-5 space-y-3">
                {roles.map((role) => {
                  const managesRoles = managedRoleMap[role.id] ?? [];
                  const managesUsers = managedUserMap[role.id] ?? [];
                  const managedBy = managedByMap[role.id] ?? [];
                  const managedByUsers = managedByUserMap[role.id] ?? [];
                  const managedByParts: string[] = [];
                  if (managedBy.length > 0) managedByParts.push(`Roles: ${managedBy.map((item) => item.name).join(", ")}`);
                  if (managedByUsers.length > 0) managedByParts.push(`Users: ${managedByUsers.map((item) => item.username).join(", ")}`);
                  const showAllManagedRoles = expandedManagedRoles.has(role.id);
                  const showAllManagedUsers = expandedManagedUsers.has(role.id);
                  const visibleManagedRoles = showAllManagedRoles ? managesRoles : managesRoles.slice(0, 5);
                  const visibleManagedUsers = showAllManagedUsers ? managesUsers : managesUsers.slice(0, 5);

                  return (
                    <div
                      key={role.id}
                      className={`rounded-xl border p-4 ${
                        darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200 bg-[#f8f8f9]"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className="rounded-full bg-blue-100 p-2 text-blue-600">
                            <Shield className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="text-lg font-semibold">{role.name}</div>
                            <div className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>{role.description || "No description"}</div>
                          </div>
                        </div>
                        <span className="inline-flex items-center rounded-md bg-purple-100 px-2 py-0.5 text-xs text-purple-700">
                          <Lock className="mr-1 h-3 w-3" />
                          clearance:{role.name.toLowerCase()}
                        </span>
                      </div>

                      {(managesRoles.length > 0 || managesUsers.length > 0) && (
                        <div className={`mt-3 border-l-2 pl-4 ${darkMode ? "border-blue-400/40" : "border-blue-200"}`}>
                          <div className={`mb-1 text-sm ${darkMode ? "text-gray-200" : "text-gray-600"}`}>Can manage:</div>
                          <div className="space-y-2">
                            {managesRoles.length > 0 && (
                              <div className="space-y-1">
                                <div className={`text-xs uppercase tracking-wide ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                  Roles
                                </div>
                                {visibleManagedRoles.map((managedRole) => (
                                  <label key={managedRole.id} className="flex items-center gap-2 text-sm">
                                    <span className={`${darkMode ? "text-blue-300" : "text-blue-500"}`}>›</span>
                                    <span
                                      className={`inline-flex rounded px-2 py-0.5 font-medium ${
                                        darkMode ? "bg-gray-700 text-gray-100" : "bg-gray-100 text-gray-800"
                                      }`}
                                    >
                                      {managedRole.name}
                                    </span>
                                    <span className={`${darkMode ? "text-gray-300" : "text-gray-400"}`}>
                                      {rolePermissionCounts[managedRole.id] ?? "—"} perms
                                    </span>
                                    {hierarchyManagerType === "role" && hierarchyManagerRoleId === role.id && (
                                      <Checkbox
                                        checked={managedRoleIds.has(managedRole.id)}
                                        onCheckedChange={(checked) =>
                                          void onToggleManagedRole(managedRole.id, checked === true)
                                        }
                                      />
                                    )}
                                  </label>
                                ))}
                                {managesRoles.length > 5 && (
                                  <Button
                                    variant="ghost"
                                    className="h-7 px-2 text-xs"
                                    onClick={() => toggleExpandedManagedRoles(role.id)}
                                  >
                                    {showAllManagedRoles ? "Show less" : `Show ${managesRoles.length - 5} more`}
                                  </Button>
                                )}
                              </div>
                            )}

                            {managesUsers.length > 0 && (
                              <div className="space-y-1">
                                <div className={`text-xs uppercase tracking-wide ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                                  Users
                                </div>
                                {visibleManagedUsers.map((managedUser) => (
                                  <label key={managedUser.id} className="flex items-center gap-2 text-sm">
                                    <span className={`${darkMode ? "text-blue-300" : "text-blue-500"}`}>›</span>
                                    <span
                                      className={`inline-flex rounded px-2 py-0.5 font-medium ${
                                        darkMode ? "bg-gray-700 text-gray-100" : "bg-gray-100 text-gray-800"
                                      }`}
                                    >
                                      {managedUser.username}
                                    </span>
                                    <span className={`${darkMode ? "text-gray-300" : "text-gray-400"}`}>
                                      {managedUser.email}
                                    </span>
                                    {hierarchyManagerType === "role" && hierarchyManagerRoleId === role.id && (
                                      <Checkbox
                                        checked={managedUserIds.has(managedUser.id)}
                                        onCheckedChange={(checked) =>
                                          void onToggleManagedUser(managedUser.id, checked === true)
                                        }
                                      />
                                    )}
                                  </label>
                                ))}
                                {managesUsers.length > 5 && (
                                  <Button
                                    variant="ghost"
                                    className="h-7 px-2 text-xs"
                                    onClick={() => toggleExpandedManagedUsers(role.id)}
                                  >
                                    {showAllManagedUsers ? "Show less" : `Show ${managesUsers.length - 5} more`}
                                  </Button>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      <div className={`mt-3 text-sm ${darkMode ? "text-gray-400" : "text-gray-500"}`}>
                        Managed by:{" "}
                        {managedByParts.length > 0 ? managedByParts.join(" • ") : "No one"}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {section === "training" && (
            <div className="px-3 py-2">
              <h2 className="text-2xl font-semibold">Training Schedule</h2>
              <p className={`mt-1 text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>
                Configure nightly retraining time for feedback and annotation data.
              </p>

              <div
                className={`mt-4 max-w-xl rounded-xl border p-4 ${
                  darkMode ? "border-gray-700 bg-gray-800" : "border-gray-200 bg-[#f8f8f9]"
                }`}
              >
                <div className="grid gap-3">
                  <label className="flex items-center gap-3 text-sm font-medium">
                    <Checkbox
                      checked={retrainEnabled}
                      onCheckedChange={(checked) => setRetrainEnabled(checked === true)}
                    />
                    Enable nightly retraining
                  </label>

                  <label className="grid gap-1">
                    <span className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>Timezone</span>
                    <input
                      className="h-10 rounded-xl border border-gray-300 bg-white px-3 text-sm text-black"
                      value={retrainTimezone}
                      onChange={(event) => setRetrainTimezone(event.target.value)}
                      placeholder="America/Los_Angeles"
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-3">
                    <label className="grid gap-1">
                      <span className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>Hour (0-23)</span>
                      <input
                        type="number"
                        min={0}
                        max={23}
                        className="h-10 rounded-xl border border-gray-300 bg-white px-3 text-sm text-black"
                        value={retrainHour}
                        onChange={(event) => setRetrainHour(Math.min(23, Math.max(0, Number(event.target.value) || 0)))}
                      />
                    </label>
                    <label className="grid gap-1">
                      <span className={`text-sm ${darkMode ? "text-gray-300" : "text-gray-600"}`}>Minute (0-59)</span>
                      <input
                        type="number"
                        min={0}
                        max={59}
                        className="h-10 rounded-xl border border-gray-300 bg-white px-3 text-sm text-black"
                        value={retrainMinute}
                        onChange={(event) => setRetrainMinute(Math.min(59, Math.max(0, Number(event.target.value) || 0)))}
                      />
                    </label>
                  </div>

                  <div>
                    <Button
                      className="rounded-xl bg-[#020825] px-4 text-sm"
                      disabled={loading}
                      onClick={onSaveRetrainSchedule}
                    >
                      Save Schedule
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
