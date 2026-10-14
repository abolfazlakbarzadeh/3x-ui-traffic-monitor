import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import RangeToolbar from "../components/RangeToolbar";
import { api } from "../api/client";
import { formatBytes } from "../lib/format";
import { defaultRange, rangeLabel, resolveRange, type UsageRange } from "../lib/ranges";
import { useTheme } from "../theme/ThemeProvider";

export default function OverviewPage() {
  const { theme } = useTheme();
  const [range, setRange] = useState<UsageRange>(() => defaultRange());
  const resolved = useMemo(() => resolveRange(range), [range]);

  const servers = useQuery({ queryKey: ["servers"], queryFn: api.servers });
  // Key on ISO bounds so preset switches (e.g. 90d → 12m) always refetch.
  const top = useQuery({
    queryKey: ["top", resolved.from ?? "", resolved.to ?? ""],
    queryFn: () => api.top({ from: resolved.from, to: resolved.to }),
  });
  const online = useQuery({ queryKey: ["online"], queryFn: api.online, refetchInterval: 30_000 });
  const users = useQuery({
    queryKey: ["users-summary"],
    queryFn: () => api.users(new URLSearchParams({ page: "1", page_size: "1" })),
  });

  const periodTotal = (top.data ?? []).reduce((s, u) => s + u.total, 0);
  const gridStroke = theme === "dark" ? "#303030" : "#f0f0f0";
  const tickFill = theme === "dark" ? "rgba(255,255,255,0.45)" : "#8c8c8c";
  const tipStyle = {
    borderRadius: 8,
    border: `1px solid ${theme === "dark" ? "#303030" : "#f0f0f0"}`,
    background: theme === "dark" ? "#1f1f1f" : "#fff",
    color: theme === "dark" ? "rgba(255,255,255,0.85)" : "#262626",
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="xui-page-title">Dashboard</h1>
        <p className="xui-page-desc">
          Traffic vitals · observing <span className="text-panel-text">{rangeLabel(range)}</span>
        </p>
      </div>

      <RangeToolbar
        range={range}
        onChange={setRange}
        title="Dashboard range"
        hint={
          range.mode === "preset" && range.preset === "12m"
            ? "12m = last 12 minutes (same idea as Last → 12 → minute). Use 1y for twelve months."
            : range.mode === "preset" && range.preset === "1y"
              ? "1y = last 12 calendar months of traffic recorded by this monitor."
              : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Top users (range sum)" value={formatBytes(periodTotal)} accent="primary" />
        <Stat label="Online now" value={String(online.data?.length ?? 0)} accent="success" />
        <Stat label="Tracked clients" value={String(users.data?.total ?? "—")} accent="warning" />
      </div>

      <section className="xui-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-panel-text">Servers</h2>
          <span className="text-xs text-panel-muted">{servers.data?.length ?? 0} panel(s)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {(servers.data ?? []).map((s) => (
            <a
              key={s.id}
              href={s.panel_url || s.base_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-md border border-panel-border bg-panel-soft px-3 py-2 text-sm transition-colors hover:border-primary hover:bg-primary-soft"
              title={s.last_error ? s.last_error : `Open ${s.name} panel`}
            >
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  s.last_poll_ok
                    ? "bg-success"
                    : s.last_poll_ok === false
                      ? "bg-danger"
                      : "bg-panel-muted"
                }`}
              />
              <span className="font-medium text-panel-text">{s.name}</span>
              <span className="xui-tag bg-primary-soft text-primary">{s.source_mode}</span>
              <ExternalLinkIcon />
            </a>
          ))}
          {!servers.data?.length && (
            <p className="text-sm text-panel-muted">
              No panels configured yet. Set <code className="text-xs">XUI_SERVERS</code> or{" "}
              <code className="text-xs">servers.yaml</code>.
            </p>
          )}
        </div>
      </section>

      <section className="xui-card p-4">
        <h2 className="mb-3 text-base font-semibold text-panel-text">
          Top 10 · {rangeLabel(range)}
        </h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={top.data ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis
                dataKey="email"
                tick={{ fontSize: 11, fill: tickFill }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={70}
              />
              <YAxis
                tickFormatter={(v) => formatBytes(Number(v))}
                width={72}
                tick={{ fontSize: 11, fill: tickFill }}
              />
              <Tooltip formatter={(v: number) => formatBytes(v)} contentStyle={tipStyle} />
              <Bar dataKey="total" fill="#1677ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="xui-table-wrap mt-4 border-0 shadow-none">
          <table className="xui-table">
            <thead>
              <tr>
                <th className="w-12">#</th>
                <th>Email</th>
                <th>Server</th>
                <th>Up</th>
                <th>Down</th>
                <th>Total</th>
                <th className="w-16">Share</th>
              </tr>
            </thead>
            <tbody>
              {(top.data ?? []).map((u, idx) => {
                const share = periodTotal > 0 ? (u.total / periodTotal) * 100 : 0;
                return (
                  <tr key={`${u.server_id}-${u.email}`}>
                    <td className="font-mono text-xs text-panel-muted">{idx + 1}</td>
                    <td>
                      <Link
                        className="font-medium text-primary hover:text-primary-hover"
                        to={`/users/${u.server_id}/${encodeURIComponent(u.email)}`}
                      >
                        {u.email}
                      </Link>
                    </td>
                    <td className="text-panel-muted">{u.server_name}</td>
                    <td className="font-mono text-xs" title={`${u.up.toLocaleString()} bytes`}>
                      {formatBytes(u.up)}
                    </td>
                    <td className="font-mono text-xs" title={`${u.down.toLocaleString()} bytes`}>
                      {formatBytes(u.down)}
                    </td>
                    <td className="font-mono text-xs font-medium" title={`${u.total.toLocaleString()} bytes`}>
                      {formatBytes(u.total)}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel-soft">
                          <div
                            className="h-full rounded-full bg-primary"
                            style={{ width: `${Math.min(100, share)}%` }}
                          />
                        </div>
                        <span className="w-10 text-right font-mono text-[11px] text-panel-muted">
                          {share.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!top.data?.length && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-panel-muted">
                    No usage in this range yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "primary" | "success" | "warning";
}) {
  const bar =
    accent === "primary" ? "bg-primary" : accent === "success" ? "bg-success" : "bg-warning";
  return (
    <div className="xui-card relative overflow-hidden p-4">
      <div className={`absolute inset-y-0 left-0 w-1 ${bar}`} />
      <p className="text-xs text-panel-muted">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold tracking-tight text-panel-text">{value}</p>
    </div>
  );
}

function ExternalLinkIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="text-panel-muted"
      aria-hidden
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}
