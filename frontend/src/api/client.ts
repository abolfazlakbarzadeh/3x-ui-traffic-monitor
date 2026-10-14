import { apiUrl } from "../lib/basePath";

export type Server = {
  id: number;
  name: string;
  base_url: string;
  web_base_path: string;
  panel_url: string;
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

export type PanelSettings = {
  web_listen: string;
  web_domain: string;
  web_port: number;
  web_cert_file: string;
  web_key_file: string;
  web_base_path: string;
  tls_enabled: boolean;
  restarting?: boolean;
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
  const res = await fetch(apiUrl(path), { ...init, headers, credentials: "include" });
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
  logout: () => request<{ success: boolean }>("/api/auth/logout", { method: "POST" }),
  me: () => request<{ username: string; role: string }>("/api/auth/me"),
  servers: () => request<Server[]>("/api/servers"),
  users: (params: URLSearchParams) =>
    request<{ items: UserRow[]; total: number; page: number; page_size: number }>(
      `/api/users?${params}`,
    ),
  top: (opts: { period?: "day" | "month"; from?: string; to?: string } = {}) => {
    const params = new URLSearchParams();
    params.set("period", opts.period ?? "day");
    if (opts.from) params.set("from", opts.from);
    if (opts.to) params.set("to", opts.to);
    return request<
      Array<{
        server_id: number;
        email: string;
        server_name: string;
        total: number;
        up: number;
        down: number;
      }>
    >(`/api/usage/top?${params}`);
  },
  online: () =>
    request<Array<{ email: string; server_name: string; started_at: string }>>("/api/online"),
  usage: (
    serverId: number,
    email: string,
    granularity: string,
    range?: { from?: string; to?: string },
  ) => {
    const params = new URLSearchParams({ granularity });
    if (range?.from) params.set("from", range.from);
    if (range?.to) params.set("to", range.to);
    return request<{
      points: Array<{ bucket_start: string; up: number; down: number }>;
      resets: Array<{ ts: string; reason: string }>;
    }>(`/api/users/${serverId}/${encodeURIComponent(email)}/usage?${params}`);
  },
  sessions: (serverId: number, email: string) =>
    request<Array<{ started_at: string; ended_at: string | null }>>(
      `/api/users/${serverId}/${encodeURIComponent(email)}/sessions`,
    ),
  exportUrl: (params: URLSearchParams) => apiUrl(`/api/export.csv?${params}`),
  panelSettings: () => request<PanelSettings>("/api/settings/panel"),
  savePanelSettings: (body: Omit<PanelSettings, "tls_enabled" | "restarting"> & { restart?: boolean }) =>
    request<PanelSettings>("/api/settings/panel", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
};
