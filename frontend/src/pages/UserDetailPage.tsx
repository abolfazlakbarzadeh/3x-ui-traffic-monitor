import { useMemo, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import RangeToolbar from "../components/RangeToolbar";
import { api } from "../api/client";
import { formatBytes } from "../lib/format";
import {
  defaultRange,
  pickGranularity,
  rangeLabel,
  resolveRange,
  sumPoints,
  isCompactUsageView,
  type UsageRange,
} from "../lib/ranges";
import { useTheme } from "../theme/ThemeProvider";

export default function UserDetailPage() {
  const { theme } = useTheme();
  const { serverId, email } = useParams();
  const sid = Number(serverId);
  const decoded = decodeURIComponent(email || "");

  const [range, setRange] = useState<UsageRange>(() => defaultRange());
  const resolved = useMemo(() => resolveRange(range), [range]);
  const compact = useMemo(
    () => isCompactUsageView(range, resolved),
    [range, resolved],
  );
  const spanMs = useMemo(() => {
    if (!resolved.from || !resolved.to) return null;
    return Math.max(0, new Date(resolved.to).getTime() - new Date(resolved.from).getTime());
  }, [resolved]);
  const fineGrain = spanMs != null && spanMs <= 3 * 60 * 60 * 1000;
  const compactGranularity = useMemo(
    () => pickGranularity(spanMs ?? 48 * 60 * 60 * 1000),
    [spanMs],
  );

  const hourly = useQuery({
    queryKey: ["usage", sid, decoded, "hour", resolved],
    queryFn: () => api.usage(sid, decoded, "hour", resolved),
    enabled: Boolean(sid && decoded) && !compact,
  });
  const daily = useQuery({
    queryKey: ["usage", sid, decoded, "day", resolved],
    queryFn: () => api.usage(sid, decoded, "day", resolved),
    enabled: Boolean(sid && decoded) && !compact,
  });
  const monthly = useQuery({
    queryKey: ["usage", sid, decoded, "month", resolved],
    queryFn: () => api.usage(sid, decoded, "month", resolved),
    enabled: Boolean(sid && decoded) && !compact,
  });
  const compactSeries = useQuery({
    queryKey: ["usage", sid, decoded, compactGranularity, resolved, "compact"],
    queryFn: () => api.usage(sid, decoded, compactGranularity, resolved),
    enabled: Boolean(sid && decoded) && compact,
  });
  const sessions = useQuery({
    queryKey: ["sessions", sid, decoded],
    queryFn: () => api.sessions(sid, decoded),
    enabled: Boolean(sid && decoded),
  });

  // Present short/medium presets still show 3 charts; totals follow the span grain
  // (day for 7d–90d) so we don't sum a sparse hourly series while daily is the truth.
  const totalsSeries = compact
    ? compactSeries.data
    : compactGranularity === "day"
      ? daily.data
      : hourly.data;
  const rangeTotals = useMemo(() => sumPoints(totalsSeries?.points), [totalsSeries?.points]);
  const resets = (compact ? compactSeries.data?.resets : hourly.data?.resets) ?? [];

  const compactTitle =
    compactGranularity === "hour"
      ? "Hourly"
      : compactGranularity === "day"
        ? "Daily"
        : "Monthly";
  const compactBadge =
    range.mode === "last"
      ? "last window"
      : range.mode === "preset"
        ? "present range"
        : "historical window";

  return (
    <div className="space-y-4">
      <div>
        <Link to="/users" className="text-sm text-primary hover:text-primary-hover">
          ← Clients
        </Link>
        <h1 className="xui-page-title mt-1">{decoded}</h1>
        <p className="xui-page-desc">
          Server #{sid} · Observing <span className="text-panel-text">{rangeLabel(range)}</span>
          {compact && (
            <span className="ml-2 xui-tag bg-warning/15 text-warning">{compactBadge}</span>
          )}
        </p>
      </div>

      <RangeToolbar
        range={range}
        onChange={setRange}
        hint={
          fineGrain
            ? "Short window: chart uses per-poll snapshots (≈ minute resolution), not full-hour buckets."
            : compact && range.mode === "preset" && range.preset === "1y"
              ? "1y window: monthly chart plus total consumed in range (not lifetime quota)."
              : compact
                ? "Showing one chart for this window plus total consumed."
                : null
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <TotalCard label="Total in range" value={formatBytes(rangeTotals.total)} accent="primary" />
        <TotalCard label="Upload" value={formatBytes(rangeTotals.up)} accent="up" />
        <TotalCard label="Download" value={formatBytes(rangeTotals.down)} accent="down" />
      </div>

      {compact ? (
        <ChartBlock
          title={`${compactTitle} · ${rangeLabel(range)}`}
          data={compactSeries.data?.points}
          loading={compactSeries.isFetching}
          theme={theme}
          footer={
            <p className="mt-2 text-xs text-panel-muted">
              Consumed in range:{" "}
              <span className="font-mono text-panel-text">{formatBytes(rangeTotals.total)}</span>
              {" · "}
              <span className="font-mono">{formatBytes(rangeTotals.up)}</span> up /{" "}
              <span className="font-mono">{formatBytes(rangeTotals.down)}</span> down
            </p>
          }
        />
      ) : (
        <>
          <ChartBlock
            title="Hourly"
            data={hourly.data?.points}
            loading={hourly.isFetching}
            theme={theme}
          />
          <ChartBlock
            title="Daily"
            data={daily.data?.points}
            loading={daily.isFetching}
            theme={theme}
          />
          <ChartBlock
            title="Monthly"
            data={monthly.data?.points}
            loading={monthly.isFetching}
            theme={theme}
          />
        </>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="xui-card p-4">
          <h3 className="mb-3 text-sm font-semibold text-panel-text">Reset events</h3>
          <ul className="max-h-56 space-y-2 overflow-auto text-sm">
            {resets.length === 0 && (
              <li className="text-panel-muted">No resets in this window.</li>
            )}
            {resets.map((r) => (
              <li
                key={r.ts}
                className="flex items-center justify-between gap-2 rounded-md bg-panel-soft px-3 py-2"
              >
                <span className="xui-tag bg-warning/15 text-warning">{r.reason}</span>
                <span className="font-mono text-xs text-panel-muted">{r.ts}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="xui-card p-4">
          <h3 className="mb-3 text-sm font-semibold text-panel-text">Online sessions</h3>
          <ul className="max-h-56 space-y-2 overflow-auto text-sm">
            {(sessions.data ?? []).length === 0 && (
              <li className="text-panel-muted">No sessions recorded yet.</li>
            )}
            {(sessions.data ?? []).map((s) => (
              <li
                key={s.started_at}
                className="flex items-center justify-between gap-2 rounded-md bg-panel-soft px-3 py-2 font-mono text-xs"
              >
                <span className="text-panel-text">{s.started_at}</span>
                <span className={s.ended_at ? "text-panel-muted" : "text-success"}>
                  {s.ended_at ?? "online"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function TotalCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "primary" | "up" | "down";
}) {
  const bar =
    accent === "primary" ? "bg-primary" : accent === "up" ? "bg-[#1677ff]" : "bg-[#13c2c2]";
  return (
    <div className="xui-card relative overflow-hidden p-4">
      <div className={`absolute inset-y-0 left-0 w-1 ${bar}`} />
      <p className="text-xs text-panel-muted">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold tracking-tight text-panel-text">{value}</p>
    </div>
  );
}

function ChartBlock({
  title,
  data,
  loading,
  theme,
  footer,
}: {
  title: string;
  data?: Array<{ bucket_start: string; up: number; down: number }>;
  loading?: boolean;
  theme: "light" | "dark";
  footer?: ReactNode;
}) {
  const chartData = (data ?? []).map((p) => ({
    ...p,
    label: new Date(p.bucket_start).toLocaleString(),
  }));
  const gridStroke = theme === "dark" ? "#303030" : "#f0f0f0";
  const tickFill = theme === "dark" ? "rgba(255,255,255,0.45)" : "#8c8c8c";
  const tipStyle = {
    borderRadius: 8,
    border: `1px solid ${theme === "dark" ? "#303030" : "#f0f0f0"}`,
    background: theme === "dark" ? "#1f1f1f" : "#fff",
    color: theme === "dark" ? "rgba(255,255,255,0.85)" : "#262626",
  };
  return (
    <section className="xui-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-panel-text">{title}</h3>
        {loading && <span className="text-xs text-primary">updating…</span>}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="label" hide />
            <YAxis
              tickFormatter={(v) => formatBytes(Number(v))}
              width={72}
              tick={{ fontSize: 11, fill: tickFill }}
            />
            <Tooltip formatter={(v: number) => formatBytes(v)} contentStyle={tipStyle} />
            <Legend />
            <Area
              type="monotone"
              dataKey="up"
              stackId="1"
              stroke="#1677ff"
              fill="#1677ff"
              fillOpacity={0.35}
            />
            <Area
              type="monotone"
              dataKey="down"
              stackId="1"
              stroke="#13c2c2"
              fill="#13c2c2"
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {footer}
    </section>
  );
}
