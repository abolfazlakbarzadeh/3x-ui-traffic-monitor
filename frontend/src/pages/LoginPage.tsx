import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useTheme } from "../theme/ThemeProvider";

export default function LoginPage() {
  const { theme, toggleTheme } = useTheme();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const qc = useQueryClient();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(username, password);
      // Force a fresh /me after staleTime: Infinity on the auth query
      await qc.resetQueries({ queryKey: ["me"] });
      await qc.fetchQuery({ queryKey: ["me"], queryFn: api.me });
      nav("/");
    } catch {
      setError("Invalid credentials");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-scene grid place-items-center px-4" data-theme={theme}>
      <div className="login-blob" aria-hidden />
      <button
        type="button"
        onClick={toggleTheme}
        className="absolute right-4 top-4 z-20 rounded-md border border-panel-line bg-panel-card/90 px-3 py-1.5 text-xs text-panel-text shadow-card backdrop-blur hover:border-primary hover:text-primary"
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? "Light" : "Dark"}
      </button>
      <form
        onSubmit={onSubmit}
        className="relative z-10 w-full max-w-[380px] rounded-ant border border-panel-border bg-panel-card p-8 shadow-popup"
      >
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-sider text-sm font-bold text-white">
            3X
          </div>
          <h1 className="text-2xl font-semibold text-panel-text">Welcome</h1>
          <p className="mt-1 text-sm text-panel-muted">Sign in to X-UI Traffic Monitor</p>
        </div>

        <label className="mb-4 block text-sm text-panel-text">
          Username
          <input
            className="xui-input mt-1.5 w-full"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="mb-4 block text-sm text-panel-text">
          Password
          <input
            type="password"
            className="xui-input mt-1.5 w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>

        {error && (
          <div className="mb-4 rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
            {error}
          </div>
        )}

        <button type="submit" disabled={busy} className="xui-btn-primary h-10 w-full">
          {busy ? "Signing in…" : "Login"}
        </button>

        <p className="mt-5 text-center text-xs text-panel-muted">
          Companion panel for 3x-ui · read-only traffic history
        </p>
      </form>
    </div>
  );
}
