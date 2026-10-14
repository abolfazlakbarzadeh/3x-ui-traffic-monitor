import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type PanelSettings } from "../api/client";

type FormState = {
  web_listen: string;
  web_domain: string;
  web_port: number;
  web_cert_file: string;
  web_key_file: string;
  web_base_path: string;
};

function fromSettings(s: PanelSettings): FormState {
  return {
    web_listen: s.web_listen,
    web_domain: s.web_domain,
    web_port: s.web_port,
    web_cert_file: s.web_cert_file,
    web_key_file: s.web_key_file,
    web_base_path: s.web_base_path,
  };
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["panel-settings"], queryFn: api.panelSettings });
  const [form, setForm] = useState<FormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [restartHint, setRestartHint] = useState(false);

  useEffect(() => {
    if (settings.data) setForm(fromSettings(settings.data));
  }, [settings.data]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await api.savePanelSettings({ ...form, restart: true });
      await qc.invalidateQueries({ queryKey: ["panel-settings"] });
      if (saved.restarting) {
        setRestartHint(true);
        // Give the process a moment to exit, then reload once Docker brings it back.
        window.setTimeout(() => {
          window.location.reload();
        }, 2500);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  if (settings.isPending || !form) {
    return <p className="text-sm text-panel-muted">Loading panel settings…</p>;
  }

  if (settings.isError) {
    return (
      <p className="text-sm text-danger">
        Failed to load settings (admin only). {String(settings.error)}
      </p>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="xui-page-title">Panel settings</h1>
        <p className="xui-page-desc">
          Listen address, domain, port, TLS files, and URL base path — same idea as 3x-ui General
          settings. Saved to SQLite; the process restarts so Docker picks up the new bind.
        </p>
      </div>

      <div className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-panel-text">
        After changing <span className="font-mono">web_port</span>, update Docker Compose{" "}
        <span className="font-mono">ports:</span> so the host still maps to that container port.
        Cert/key paths must be readable inside the container (mount them under{" "}
        <span className="font-mono">/config</span>).
      </div>

      <form onSubmit={onSubmit} className="xui-card space-y-4 p-4">
        <Field
          label="Listen IP"
          hint="Empty = all interfaces (0.0.0.0). Use 127.0.0.1 for local-only."
        >
          <input
            className="xui-input w-full font-mono"
            value={form.web_listen}
            onChange={(e) => setForm({ ...form, web_listen: e.target.value })}
            placeholder="0.0.0.0"
          />
        </Field>

        <Field
          label="Listen domain"
          hint="When set, only this Host header is accepted (403 otherwise). Leave empty to allow all."
        >
          <input
            className="xui-input w-full font-mono"
            value={form.web_domain}
            onChange={(e) => setForm({ ...form, web_domain: e.target.value })}
            placeholder="monitor.example.com"
          />
        </Field>

        <Field label="Port" hint="1–65535. Default 8000.">
          <input
            type="number"
            min={1}
            max={65535}
            className="xui-input w-full font-mono"
            value={form.web_port}
            onChange={(e) => setForm({ ...form, web_port: Number(e.target.value) || 8000 })}
          />
        </Field>

        <Field label="Certificate file" hint="Absolute path inside the container.">
          <input
            className="xui-input w-full font-mono"
            value={form.web_cert_file}
            onChange={(e) => setForm({ ...form, web_cert_file: e.target.value })}
            placeholder="/config/certs/fullchain.pem"
          />
        </Field>

        <Field label="Key file" hint="Both cert and key must be set to enable HTTPS.">
          <input
            className="xui-input w-full font-mono"
            value={form.web_key_file}
            onChange={(e) => setForm({ ...form, web_key_file: e.target.value })}
            placeholder="/config/certs/privkey.pem"
          />
        </Field>

        {/*
          ★ Learning contribution spot: normalizeBasePath()
          Decide how aggressive normalization should be (always trailing slash?
          reject empty segments? allow nested paths only?).
        */}
        <Field
          label="Web base path"
          hint="URL prefix for the panel (e.g. /secret). Use / for the site root."
        >
          <input
            className="xui-input w-full font-mono"
            value={form.web_base_path}
            onChange={(e) => setForm({ ...form, web_base_path: e.target.value })}
            placeholder="/"
          />
        </Field>

        {error && (
          <div className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
            {error}
          </div>
        )}
        {restartHint && (
          <div className="rounded-md border border-primary/30 bg-primary-soft px-3 py-2 text-sm text-primary">
            Settings saved — restarting panel… This page will reload shortly.
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button type="submit" disabled={busy || restartHint} className="xui-btn-primary">
            {busy ? "Saving…" : "Save & restart"}
          </button>
          {settings.data?.tls_enabled && (
            <span className="xui-tag bg-success/15 text-success">TLS on</span>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block text-sm text-panel-text">
      <span className="font-medium">{label}</span>
      {hint && <span className="mt-0.5 block text-xs font-normal text-panel-muted">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
