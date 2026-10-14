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
import { api } from "../api/client";
import { formatBytes } from "../lib/format";

export default function OverviewPage() {
  const servers = useQuery({ queryKey: ["servers"], queryFn: api.servers });
  const top = useQuery({ queryKey: ["top", "day"], queryFn: () => api.top("day") });
  const online = useQuery({ queryKey: ["online"], queryFn: api.online, refetchInterval: 30_000 });
  const users = useQuery({
    queryKey: ["users-summary"],
    queryFn: () => api.users(new URLSearchParams({ page: "1", page_size: "1" })),
  });

  const todayTotal = (top.data ?? []).reduce((s, u) => s + u.total, 0);

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-xl font-semibold">Today at a glance</h2>
        <p className="text-sm text-ink/60">Totals from hourly deltas in the configured timezone.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Stat label="Top users today (sum)" value={formatBytes(todayTotal)} />
          <Stat label="Online now" value={String(online.data?.length ?? 0)} />
          <Stat label="Tracked clients" value={String(users.data?.total ?? "—")} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Servers</h2>
        <div className="flex flex-wrap gap-2">
          {(servers.data ?? []).map((s) => (
            <div
              key={s.id}
              className="border border-line bg-white/60 px-3 py-2 text-sm"
              title={s.last_error ?? undefined}
            >
              <span
                className={`mr-2 inline-block h-2 w-2 rounded-full ${
                  s.last_poll_ok ? "bg-leaf" : s.last_poll_ok === false ? "bg-clay" : "bg-line"
                }`}
              />
              {s.name}
              <span className="ml-2 font-mono text-xs text-ink/50">{s.source_mode}</span>
            </div>
          ))}
          {!servers.data?.length && (
            <p className="text-sm text-ink/50">No panels configured yet. Set XUI_SERVERS or servers.yaml.</p>
          )}
        </div>
      </section>

      <section className="h-80">
        <h2 className="mb-3 text-xl font-semibold">Top 10 today</h2>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={top.data ?? []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#c5d4cc" />
            <XAxis dataKey="email" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={70} />
            <YAxis tickFormatter={(v) => formatBytes(Number(v))} width={72} />
            <Tooltip formatter={(v: number) => formatBytes(v)} />
            <Bar dataKey="total" fill="#1f6f54" />
          </BarChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-line bg-white/50 px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-ink/50">{label}</p>
      <p className="mt-1 font-mono text-2xl">{value}</p>
    </div>
  );
}
