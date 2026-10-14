# xui-traffic-monitor Design

**Date:** 2026-10-14  
**Status:** Approved  
**Source:** `/home/abolfazl-akbarzadeh/Downloads/3x-ui-monitor-prompt.md` + design session decisions

## Goal

Self-hosted web app that adds per-client traffic history (hourly, daily, monthly) for one or more 3x-ui panels. Polls panels read-only, stores time-series deltas in Postgres, serves a React dashboard.

## Locked decisions

- FastAPI serves built React SPA as static files (no nginx in Compose)
- Plain PostgreSQL 16 (no TimescaleDB); day/month = `SUM(usage_hourly)` in configured `TZ`
- Workspace root layout (not nested `xui-traffic-monitor/`)
- Prompt-faithful full stack (API + SQLite + legacy adapters, mock panel tests, JWT monitor auth)
- `ALLOW_WRITE_ACTIONS=false` by default; never auto-call 3x-ui write endpoints

## Architecture

```
Browser → FastAPI (API + static SPA) → Postgres
                ↓ poll (read-only)
           3x-ui panels (API or SQLite RO)
```

Compose services: `app` (non-root, multi-stage) + `db` (Postgres 16). Optional reverse proxy in front of the whole stack (documented, not in compose).

### Components

- **Poller** (asyncio): traffic every `POLL_INTERVAL_SECONDS` (60), online every `ONLINE_POLL_SECONDS` (30)
- **TrafficSource** protocol: `xui_api`, `xui_sqlite`, `xui_legacy`
- **Delta engine**: cumulative counters → non-negative deltas; detects resets
- **Monitor API**: JWT httpOnly cookie; 3x-ui tokens never exposed to browser
- **Frontend**: React + Vite + TS + TanStack Query/Table + Recharts + Tailwind

## Data model

Identity: `(server_id, email)`.

| Table | Purpose |
|---|---|
| `servers` | Config mirror + last poll status/error |
| `raw_snapshots` | Per-poll counters; pruned after `RAW_RETENTION_DAYS` |
| `usage_hourly` | Upserted deltas `(server_id, email, hour_start, up, down)` |
| `counter_resets` | Reset events |
| `online_sessions` | Online start/end; open row = online now |
| `clients_current` | Latest metadata for list UI |

Day/month boundaries use `TZ` (default `Asia/Tehran`). Failed poll writes nothing; next success covers the gap in that poll's hour.

### Delta rules

1. First snapshot → baseline, delta 0  
2. Normal: `d = cur - prev`, clamp ≥ 0  
3. Reset if `cur < prev` OR `reset_count` up OR `client_id` changed → `d = cur`, emit `counter_reset`  
4. Anomaly if delta > `MAX_SANE_BYTES_PER_SEC × interval` → keep + flag  

## 3x-ui integration

Base: `{scheme}://{host}:{port}{webBasePath}/panel/api`. Response wrapper `{success, msg, obj}`.

**Auth:** Bearer admin-scope token preferred (monitor scope insufficient). Password + CSRF fallback. Send `X-Requested-With: XMLHttpRequest`.

**Endpoints used:** `/clients/list`, `/clients/list/paged`, `/clients/traffic/:email`, `/clients/get/:email`, `/inbounds/list`, `/inbounds/list/slim`, `POST /clients/onlines`, `/clients/lastOnline`, `/clients/onlinesByGuid`, `/server/status`, `/openapi.json`.

**Never auto-call:** reset/update traffic endpoints unless `ALLOW_WRITE_ACTIONS=true`.

Legacy: 404 on `/clients/list` → best-effort legacy adapter.

SQLite mode: RO mount, no online API; derive activity from `last_online`.

## Monitor API

`POST /api/auth/login`, `GET /api/servers`, `GET /api/users`, `GET /api/users/{server}/{email}/usage`, `GET /api/usage/top`, `GET /api/online`, `GET /api/export.csv`, `GET /healthz`.

## UI

Overview (totals, top-10, online, server health), users table (search/sort/filter/quota/expiry/CSV), user detail (hourly/daily/monthly charts, resets, sessions). Bytes IEC; times in `TZ`.

## Security

Read-only toward 3x-ui; argon2 + JWT cookie; CSRF on monitor POSTs; login rate limit; TLS verify default on; recommend reverse proxy.

## Acceptance

Matches prompt §9: compose up healthy, mock multi-server poller, delta unit tests, TZ aggregates, 5k-client pagination target, CSV match, OpenAPI warn, monitor-scope clear error, no write calls by default, README coverage.
