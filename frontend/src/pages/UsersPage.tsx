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
          <h1 className="xui-page-title">Clients</h1>
          <p className="xui-page-desc">Search, sort, and export traffic usage across panels.</p>
        </div>
        <a className="xui-btn-default" href={api.exportUrl(params)}>
          Export CSV
        </a>
      </div>

      <div className="xui-card flex flex-wrap gap-2 p-3">
        <input
          className="xui-input min-w-[14rem] flex-1"
          placeholder="Search email…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          className="xui-input"
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

      <div className="xui-table-wrap">
        <table className="xui-table">
          <thead>
            <tr>
              {[
                ["email", "Email"],
                ["used", "Used"],
                ["total", "Quota"],
                ["usage_today", "Today"],
                ["usage_month", "Month"],
                ["expiry", "Expiry"],
              ].map(([key, label]) => (
                <th
                  key={key}
                  className="cursor-pointer select-none hover:text-primary"
                  onClick={() => toggleSort(key)}
                >
                  {label}
                  {sort === key ? (order === "asc" ? " ↑" : " ↓") : ""}
                </th>
              ))}
              <th>Online</th>
            </tr>
          </thead>
          <tbody>
            {(users.data?.items ?? []).map((u) => {
              const pct = u.total > 0 ? Math.min(100, (u.used / u.total) * 100) : 0;
              const bar =
                u.total === 0
                  ? "bg-primary/40"
                  : pct >= 100
                    ? "bg-danger"
                    : pct >= 80
                      ? "bg-warning"
                      : "bg-success";
              const badge = expiryBadge(u.expiry_time, u.days_left);
              const badgeClass =
                badge.tone === "bad"
                  ? "bg-danger/10 text-danger"
                  : badge.tone === "warn"
                    ? "bg-warning/10 text-[#d48806]"
                    : badge.tone === "delay"
                      ? "bg-primary-soft text-primary"
                      : "bg-[rgba(0,0,0,0.04)] text-panel-muted";
              return (
                <tr key={`${u.server_id}-${u.email}`}>
                  <td>
                    <Link
                      className="font-medium text-primary hover:text-primary-hover"
                      to={`/users/${u.server_id}/${encodeURIComponent(u.email)}`}
                    >
                      {u.email}
                    </Link>
                    <div className="text-xs text-panel-muted">{u.server_name}</div>
                  </td>
                  <td className="font-mono text-xs" title={`${u.used.toLocaleString()} bytes`}>
                    {formatBytes(u.used)}
                    <div className="mt-1.5 h-1.5 w-28 overflow-hidden rounded-full bg-[rgba(0,0,0,0.06)]">
                      <div className={`h-full rounded-full ${bar}`} style={{ width: `${u.total ? pct : 8}%` }} />
                    </div>
                  </td>
                  <td className="font-mono text-xs" title={u.total ? `${u.total.toLocaleString()} bytes` : "unlimited"}>
                    {u.total === 0 ? "∞" : formatBytes(u.total)}
                  </td>
                  <td className="font-mono text-xs" title={`${u.usage_today.toLocaleString()} bytes`}>
                    {formatBytes(u.usage_today)}
                  </td>
                  <td className="font-mono text-xs" title={`${u.usage_month.toLocaleString()} bytes`}>
                    {formatBytes(u.usage_month)}
                  </td>
                  <td>
                    <span className={`xui-tag ${badgeClass}`}>{badge.label}</span>
                  </td>
                  <td>
                    <span
                      className={`inline-block h-2.5 w-2.5 rounded-full ${
                        u.online ? "bg-success shadow-[0_0_0_3px_rgba(82,196,26,0.2)]" : "bg-[#d9d9d9]"
                      }`}
                      title={u.online ? "online" : "offline"}
                    />
                  </td>
                </tr>
              );
            })}
            {!users.data?.items.length && (
              <tr>
                <td colSpan={7} className="py-10 text-center text-panel-muted">
                  No clients found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-panel-muted">{users.data?.total ?? 0} clients</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="xui-btn-default"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Prev
          </button>
          <span className="rounded-md bg-white px-2.5 py-1 font-mono text-xs text-panel-muted shadow-sm">
            {page}
          </span>
          <button
            type="button"
            className="xui-btn-default"
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
