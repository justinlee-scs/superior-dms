import { apiFetch } from "@/lib/api";

export type PermissionEffect = "ALLOW" | "DENY";

export type Permission = {
  id: string;
  key: string;
  description: string | null;
};

export type Role = {
  id: string;
  name: string;
  description: string | null;
};

export type RoleWithPermissions = Role & {
  permissions: Permission[];
};

export type User = {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  roles: Role[];
};

export type UserPermissionsResponse = {
  user_id: string;
  default_permissions: string[];
  effective_permissions: string[];
  overrides: Record<string, PermissionEffect>;
};

export type AccessMeResponse = {
  user: {
    id: string;
    email: string;
  };
  roles: Array<{ id: string; name: string }>;
  permissions: string[];
};

export function getMyAccess() {
  return apiFetch<AccessMeResponse>("/rbac/access/me");
}

export function listRoles() {
  return apiFetch<Role[]>("/rbac/roles/");
}

export function getRole(roleId: string) {
  return apiFetch<RoleWithPermissions>(`/rbac/roles/${roleId}`);
}

export function createRole(payload: { name: string; description?: string }) {
  return apiFetch<Role>("/rbac/roles/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRole(roleId: string, payload: { name?: string; description?: string }) {
  return apiFetch<Role>(`/rbac/roles/${roleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function setRolePermissions(roleId: string, permissionKeys: string[]) {
  return apiFetch<{ status: string; permission_keys: string[] }>(`/rbac/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permission_keys: permissionKeys }),
  });
}

export function copyRolePermissions(roleId: string, sourceRoleId: string) {
  return apiFetch<{ status: string; permission_keys: string[] }>(
    `/rbac/roles/${roleId}/copy-from/${sourceRoleId}`,
    { method: "POST" },
  );
}

export function listManagedRoles(roleId: string) {
  return apiFetch<Role[]>(`/rbac/roles/${roleId}/managed-roles`);
}

export function listManagedUsers(roleId: string) {
  return apiFetch<User[]>(`/rbac/roles/${roleId}/managed-users`);
}

export function addManagedRole(roleId: string, managedRoleId: string) {
  return apiFetch<{ status: string }>(`/rbac/roles/${roleId}/managed-roles/${managedRoleId}`, {
    method: "POST",
  });
}

export function addManagedUser(roleId: string, managedUserId: string) {
  return apiFetch<{ status: string }>(`/rbac/roles/${roleId}/managed-users/${managedUserId}`, {
    method: "POST",
  });
}

export function removeManagedRole(roleId: string, managedRoleId: string) {
  return apiFetch<{ status: string }>(`/rbac/roles/${roleId}/managed-roles/${managedRoleId}`, {
    method: "DELETE",
  });
}

export function removeManagedUser(roleId: string, managedUserId: string) {
  return apiFetch<{ status: string }>(`/rbac/roles/${roleId}/managed-users/${managedUserId}`, {
    method: "DELETE",
  });
}

export function listPermissions() {
  return apiFetch<Permission[]>("/rbac/permissions/");
}

export function listUsers() {
  return apiFetch<User[]>("/rbac/users/");
}

export function listUserManagedRoles(userId: string) {
  return apiFetch<Role[]>(`/rbac/users/${userId}/managed-roles`);
}

export function listUserManagedUsers(userId: string) {
  return apiFetch<User[]>(`/rbac/users/${userId}/managed-users`);
}

export function createUser(payload: { username: string; email: string; password: string; is_active?: boolean }) {
  return apiFetch<User>("/rbac/users/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function setUserRoles(userId: string, roleIds: string[]) {
  return apiFetch<{ status: string; role_ids: string[] }>(`/rbac/users/${userId}/roles`, {
    method: "PUT",
    body: JSON.stringify({ role_ids: roleIds }),
  });
}

export function addUserManagedRole(userId: string, managedRoleId: string) {
  return apiFetch<{ status: string }>(`/rbac/users/${userId}/managed-roles/${managedRoleId}`, {
    method: "POST",
  });
}

export function removeUserManagedRole(userId: string, managedRoleId: string) {
  return apiFetch<{ status: string }>(`/rbac/users/${userId}/managed-roles/${managedRoleId}`, {
    method: "DELETE",
  });
}

export function addUserManagedUser(userId: string, managedUserId: string) {
  return apiFetch<{ status: string }>(`/rbac/users/${userId}/managed-users/${managedUserId}`, {
    method: "POST",
  });
}

export function removeUserManagedUser(userId: string, managedUserId: string) {
  return apiFetch<{ status: string }>(`/rbac/users/${userId}/managed-users/${managedUserId}`, {
    method: "DELETE",
  });
}

export function activateUser(userId: string) {
  return apiFetch<User>(`/rbac/users/${userId}/activate`, {
    method: "POST",
  });
}

export function deactivateUser(userId: string) {
  return apiFetch<User>(`/rbac/users/${userId}/deactivate`, {
    method: "POST",
  });
}

export function getUserPermissions(userId: string) {
  return apiFetch<UserPermissionsResponse>(`/rbac/users/${userId}/permissions`);
}

export function getUserDefaultPermissions(userId: string) {
  return apiFetch<{ user_id: string; permissions: string[] }>(`/rbac/users/${userId}/permissions/default`);
}

export function resetUserPermissionsToDefault(userId: string) {
  return apiFetch<{ status: string; permissions: string[] }>(`/rbac/users/${userId}/permissions/reset-default`, {
    method: "POST",
  });
}

export function setUserOverrides(
  userId: string,
  overrides: Array<{ permission_key: string; effect: PermissionEffect }>,
) {
  return apiFetch<{ status: string }>(`/rbac/users/${userId}/overrides`, {
    method: "PUT",
    body: JSON.stringify({ overrides }),
  });
}
