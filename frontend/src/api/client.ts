export type Server = {
  id: number;
  name: string;
  base_url: string;
  source_mode: string;
  last_poll_at: string | null;
  last_poll_ok: boolean | null;
  last_error: string | null;
};

export type UserRow = {
  server_id: number;
  server_name: string;
  email: string;
  enable: boolean;
  up: number;
  down: number;
  used: number;
  total: number;
  remaining: number | null;
  expiry_time: number;
  days_left: number | null;
  online: boolean;
  last_online: number;
  usage_today: number;
  usage_month: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const csrf = document.cookie
    .split("; ")
    .find((c) => c.startsWith("csrf_token="))
    ?.split("=")[1];
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (csrf && init?.method && init.method !== "GET") {
    headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  }
  const res = await fetch(path, { ...init, headers, credentials: "include" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ success: boolean; role: string; csrf_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ username: string; role: string }>("/api/auth/me"),
  servers: () => request<Server[]>("/api/servers"),
  users: (params: URLSearchParams) =>
    request<{ items: UserRow[]; total: number; page: number; page_size: number }>(
      `/api/users?${params}`,
    ),
  top: (period: "day" | "month") =>
    request<Array<{ email: string; server_name: string; total: number; up: number; down: number }>>(
      `/api/usage/top?period=${period}`,
    ),
  online: () =>
    request<Array<{ email: string; server_name: string; started_at: string }>>("/api/online"),
  usage: (serverId: number, email: string, granularity: string) =>
    request<{
      points: Array<{ bucket_start: string; up: number; down: number }>;
      resets: Array<{ ts: string; reason: string }>;
    }>(`/api/users/${serverId}/${encodeURIComponent(email)}/usage?granularity=${granularity}`),
  sessions: (serverId: number, email: string) =>
    request<Array<{ started_at: string; ended_at: string | null }>>(
      `/api/users/${serverId}/${encodeURIComponent(email)}/sessions`,
    ),
  exportUrl: (params: URLSearchParams) => `/api/export.csv?${params}`,
};
