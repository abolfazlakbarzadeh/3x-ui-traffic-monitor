/** Runtime base path injected by FastAPI into index.html (`window.__XUI_BASE__`). */

declare global {
  interface Window {
    __XUI_BASE__?: string;
  }
}

export function appBasePath(): string {
  const raw = typeof window !== "undefined" ? window.__XUI_BASE__ : undefined;
  if (!raw || raw === "/") return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

export function routerBasename(): string | undefined {
  const base = appBasePath();
  return base || undefined;
}

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${appBasePath()}${p}`;
}
