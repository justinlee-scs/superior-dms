import { apiFetch } from "@/lib/api";

export type CurrentUser = {
  id: string;
  email: string;
  username: string;
  roles: string[];
  permissions: string[];
  ui_dark_mode?: boolean;
  ui_view_mode?: "compact" | "grouped";
};

export function getCurrentUserProfile() {
  return apiFetch<CurrentUser>("/auth/me");
}

export function updateCurrentUserProfile(payload: {
  username?: string;
  current_password?: string;
  new_password?: string;
  ui_dark_mode?: boolean;
  ui_view_mode?: "compact" | "grouped";
}) {
  return apiFetch<CurrentUser>("/auth/me/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
