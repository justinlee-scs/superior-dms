import { API_BASE_URL } from "@/lib/api";

export type User = {
  id: string;
  email: string;
  roles: string[];
};

export async function loginRequest(email: string, password: string): Promise<{ access_token: string; user: User }> {
// get token
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Login failed");
  }

  const { access_token } = await res.json();

  // get user info
  const userRes = await fetch(`${API_BASE_URL}/access/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });

  if (!userRes.ok) {
    throw new Error("Failed to fetch user info");
  }

  const userData = await userRes.json();

  const user: User = {
    id: userData.user.id,
    email: userData.user.email,
    roles: userData.roles.map((r: any) => r.name),
  };

  return { access_token, user };
}
