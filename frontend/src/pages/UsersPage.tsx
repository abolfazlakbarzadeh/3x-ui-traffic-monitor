import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { expiryBadge, formatBytes } from "../lib/format";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [server, setServer] = useState("");
  const [sort, setSort] = useState("email");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);

  const servers = useQuery({ queryKey: ["servers"], queryFn: api.servers });
  const params = useMemo(() => {
    const p = new URLSearchParams({
      page: String(page),
      page_size: "50",
      sort,
      order,
      search,
    });
    if (server) p.set("server", server);
    return p;
  }, [page, sort, order, search, server]);

  const users = useQuery({
    queryKey: ["users", params.toString()],
    queryFn: () => api.users(params),
  });

  function toggleSort(col: string) {
    if (sort === col) setOrder((o) => (o === "asc" ? "desc" : "asc"));
    else {
      setSort(col);
      setOrder("asc");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Users</h2>
          <p className="text-sm text-ink/60">Server-side search, sort, and pagination.</p>
        </div>
        <a
          className="border border-line bg-white/70 px-3 py-2 text-sm hover:border-leaf"
          href={api.exportUrl(params)}
        >
          Export CSV
        </a>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          className="min-w-[12rem] flex-1 border border-line bg-white/70 px-3 py-2 text-sm"
          placeholder="Search email…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          className="border border-line bg-white/70 px-3 py-2 text-sm"
          value={server}
          onChange={(e) => {
            setPage(1);
            setServer(e.target.value);
          }}
        >
          <option value="">All servers</option>
          {(servers.data ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto border border-line bg-white/60">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line bg-mist/50 font-medium">
            <tr>
              {[
                ["email", "Email"],
                ["used", "Used"],
                ["total", "Quota"],
                ["usage_today", "Today"],
                ["usage_month", "Month"],
                ["expiry", "Expiry"],
              ].map(([key, label]) => (
                <th key={key} className="cursor-pointer px-3 py-2" onClick={() => toggleSort(key)}>
                  {label}
                  {sort === key ? (order === "asc" ? " ↑" : " ↓") : ""}
                </th>
              ))}
              <th className="px-3 py-2">Online</th>
            </tr>
          </thead>
          <tbody>
            {(users.data?.items ?? []).map((u) => {
              const pct = u.total > 0 ? Math.min(100, (u.used / u.total) * 100) : 0;
              const bar =
                u.total === 0 ? "bg-leaf/40" : pct >= 100 ? "bg-clay" : pct >= 80 ? "bg-amber-500" : "bg-leaf";
              const badge = expiryBadge(u.expiry_time, u.days_left);
              return (
                <tr key={`${u.server_id}-${u.email}`} className="border-b border-line/70">
                  <td className="px-3 py-2">
                    <Link
                      className="font-medium text-leaf hover:underline"
                      to={`/users/${u.server_id}/${encodeURIComponent(u.email)}`}
                    >
                      {u.email}
                    </Link>
                    <div className="font-mono text-xs text-ink/45">{u.server_name}</div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {formatBytes(u.used)}
                    <div className="mt-1 h-1.5 w-28 overflow-hidden bg-line/60">
                      <div className={`h-full ${bar}`} style={{ width: `${u.total ? pct : 8}%` }} />
                    </div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {u.total === 0 ? "∞" : formatBytes(u.total)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{formatBytes(u.usage_today)}</td>
                  <td className="px-3 py-2 font-mono text-xs">{formatBytes(u.usage_month)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`text-xs ${
                        badge.tone === "bad"
                          ? "text-clay"
                          : badge.tone === "warn"
                            ? "text-amber-700"
                            : badge.tone === "delay"
                              ? "text-leaf"
                              : "text-ink/60"
                      }`}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block h-2.5 w-2.5 rounded-full ${
                        u.online ? "bg-leaf" : "bg-line"
                      }`}
                      title={u.online ? "online" : "offline"}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-ink/50">{users.data?.total ?? 0} users</span>
        <div className="flex gap-2">
          <button
            className="border border-line px-3 py-1 disabled:opacity-40"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Prev
          </button>
          <span className="px-2 py-1 font-mono text-xs">p{page}</span>
          <button
            className="border border-line px-3 py-1 disabled:opacity-40"
            disabled={(users.data?.items.length ?? 0) < 50}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
