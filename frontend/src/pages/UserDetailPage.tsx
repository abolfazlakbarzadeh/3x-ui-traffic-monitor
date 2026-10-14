import { useParams } from "react-router-dom";
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
import { api } from "../api/client";
import { formatBytes } from "../lib/format";

export default function UserDetailPage() {
  const { serverId, email } = useParams();
  const sid = Number(serverId);
  const decoded = decodeURIComponent(email || "");

  const hourly = useQuery({
    queryKey: ["usage", sid, decoded, "hour"],
    queryFn: () => api.usage(sid, decoded, "hour"),
    enabled: Boolean(sid && decoded),
  });
  const daily = useQuery({
    queryKey: ["usage", sid, decoded, "day"],
    queryFn: () => api.usage(sid, decoded, "day"),
    enabled: Boolean(sid && decoded),
  });
  const monthly = useQuery({
    queryKey: ["usage", sid, decoded, "month"],
    queryFn: () => api.usage(sid, decoded, "month"),
    enabled: Boolean(sid && decoded),
  });
  const sessions = useQuery({
    queryKey: ["sessions", sid, decoded],
    queryFn: () => api.sessions(sid, decoded),
    enabled: Boolean(sid && decoded),
  });

  return (
    <div className="space-y-8">
      <div>
        <p className="font-mono text-xs text-ink/50">server {sid}</p>
        <h2 className="text-2xl font-semibold">{decoded}</h2>
      </div>

      <ChartBlock title="Hourly (48h)" data={hourly.data?.points} />
      <ChartBlock title="Daily (90d)" data={daily.data?.points} />
      <ChartBlock title="Monthly (12m)" data={monthly.data?.points} />

      <section>
        <h3 className="mb-2 text-lg font-semibold">Reset events</h3>
        <ul className="space-y-1 text-sm">
          {(hourly.data?.resets ?? []).length === 0 && (
            <li className="text-ink/50">No resets in this window.</li>
          )}
          {(hourly.data?.resets ?? []).map((r) => (
            <li key={r.ts} className="font-mono text-xs">
              {r.ts} · {r.reason}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-2 text-lg font-semibold">Online sessions</h3>
        <ul className="space-y-1 text-sm">
          {(sessions.data ?? []).length === 0 && (
            <li className="text-ink/50">No sessions recorded yet.</li>
          )}
          {(sessions.data ?? []).map((s) => (
            <li key={s.started_at} className="font-mono text-xs">
              {s.started_at} → {s.ended_at ?? "online"}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ChartBlock({
  title,
  data,
}: {
  title: string;
  data?: Array<{ bucket_start: string; up: number; down: number }>;
}) {
  const chartData = (data ?? []).map((p) => ({
    ...p,
    label: new Date(p.bucket_start).toLocaleString(),
  }));
  return (
    <section className="h-72">
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <ResponsiveContainer width="100%" height="90%">
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#c5d4cc" />
          <XAxis dataKey="label" hide />
          <YAxis tickFormatter={(v) => formatBytes(Number(v))} width={72} />
          <Tooltip formatter={(v: number) => formatBytes(v)} />
          <Legend />
          <Area type="monotone" dataKey="up" stackId="1" stroke="#1f6f54" fill="#1f6f54" fillOpacity={0.55} />
          <Area type="monotone" dataKey="down" stackId="1" stroke="#c45c26" fill="#c45c26" fillOpacity={0.45} />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  );
}
