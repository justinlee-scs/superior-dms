export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) throw new Error("VITE_API_BASE_URL is not defined");

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("access_token");

  const baseHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers && !(options.headers instanceof Headers) ? (options.headers as Record<string, string>) : {}),
  };

  if (token) {
    baseHeaders["Authorization"] = `Bearer ${token}`;
    console.log("Sending token:", token);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: baseHeaders,
    credentials: "include",
  });

  if (res.status === 401) {
    console.warn("Unauthorized, clearing token");
    sessionStorage.removeItem("access_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }

  if (res.status === 204) return undefined as T;

  return res.json();
}
