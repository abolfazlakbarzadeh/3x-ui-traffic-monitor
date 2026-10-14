import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export default function LoginPage() {
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
      await qc.invalidateQueries({ queryKey: ["me"] });
      nav("/");
    } catch {
      setError("Invalid credentials");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-4 border border-line bg-white/70 p-6 backdrop-blur"
      >
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-leaf">sign in</p>
          <h1 className="text-2xl font-semibold">xui traffic monitor</h1>
        </div>
        <label className="block text-sm">
          Username
          <input
            className="mt-1 w-full border border-line bg-mist/40 px-3 py-2 outline-none focus:border-leaf"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full border border-line bg-mist/40 px-3 py-2 outline-none focus:border-leaf"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="text-sm text-clay">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-leaf px-3 py-2.5 text-sm font-medium text-white hover:bg-leaf/90 disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
