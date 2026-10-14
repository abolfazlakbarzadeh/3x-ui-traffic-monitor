# 3x-ui Traffic Monitor

**Per-client traffic history for [3x-ui](https://github.com/MHSanaei/3x-ui).**

3x-ui only keeps cumulative counters. This companion polls them on a schedule, stores **reset-aware deltas**, and serves a small dashboard so you can see usage over time — not just “used so far”.

![License](https://img.shields.io/badge/license-MIT-blue)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React%20%2B%20Postgres-0ea5e9)
![Docker](https://img.shields.io/badge/deploy-docker%20compose-2496ed)

---

## Why

| In 3x-ui | With this monitor |
| --- | --- |
| Lifetime up/down totals | Hourly / daily / monthly history |
| “Who used the most today?” is hard | Top clients for any range (12m → 1y) |
| Resets wipe context | Counter resets detected and handled |
| One panel at a time | Multi-server (`server` + `email`) |

---

## Features

- **Dashboard** — range picker, top users chart + table, online count, server status badges (click through to the panel)
- **Clients** — search, sort, export CSV, expiry badges, per-server filter
- **Client detail** — usage charts, range totals, reset events, online sessions
- **Flexible ranges** — presets (`12m`, `1h`, `48h`, `7d`, `30d`, `90d`, `1y`), Last N, relative, absolute
- **Panel settings** — listen IP, domain, port, TLS cert/key, web base path (env + admin UI → SQLite)
- **Auth** — admin / optional viewer, JWT cookie + CSRF
- **Sources** — 3x-ui HTTP API (preferred) or local SQLite read-only

---

## Quick start

**Requirements:** Docker + Docker Compose.

```bash
git clone https://github.com/abolfazlakbarzadeh/3x-ui-traffic-monitor.git
cd 3x-ui-traffic-monitor

cp .env.example .env
# Set ADMIN_PASSWORD and a long JWT_SECRET

mkdir -p config
cp servers.yaml.example config/servers.yaml
# Edit config/servers.yaml with your panel URL + admin-scope API token

docker compose up -d --build
```

Open **http://localhost:8000** and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`.

> First charts fill in after a few poll cycles (`POLL_INTERVAL_SECONDS`, default 60s). History only starts when the monitor starts — it does not backfill from 3x-ui lifetime totals.

---

## Configure 3x-ui access

### API token (recommended)

1. In 3x-ui: **Settings → Security → API Token**
2. Create a token with **`admin` scope**  
   (`monitor` scope is not enough to list clients)
3. Put it in `config/servers.yaml`:

```yaml
- name: main
  base_url: https://panel.example.com:2053
  web_base_path: /your-secret-path/
  verify_tls: true
  source_mode: api
  auth:
    type: token
    token: YOUR_ADMIN_SCOPE_TOKEN
```

Or set the same structure as JSON in `XUI_SERVERS` inside `.env`.

### SQLite on the same host

```yaml
source_mode: sqlite
sqlite_path: /xui/x-ui.db
```

Mount the panel DB read-only, e.g. `/etc/x-ui:/xui:ro`. Online status is limited; activity can still be inferred from `last_online`.

---

## Environment

| Variable | Default | Notes |
| --- | --- | --- |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / — | Bootstrap login (prefer `ADMIN_PASSWORD_HASH`) |
| `JWT_SECRET` | — | **Change this** in production |
| `TZ` | `Asia/Tehran` | Day / month boundaries |
| `POLL_INTERVAL_SECONDS` | `60` | Traffic poll |
| `ONLINE_POLL_SECONDS` | `30` | Online sessions |
| `RAW_RETENTION_DAYS` | `14` | Raw snapshots |
| `HOURLY_RETENTION_DAYS` | `400` | Hourly buckets |
| `SERVERS_YAML` | `/config/servers.yaml` | Panel list (Compose) |
| `WEB_PORT` | `8000` | Must match Compose `ports:` |
| `PANEL_SETTINGS_DB` | `/config/panel.db` | UI overrides for listen/TLS |

See `.env.example` for the full list (viewer user, TLS paths, base path, etc.).

---

## Panel settings (this app)

Admin **Settings** (sidebar) mirrors 3x-ui-style panel options:

- Listen IP / domain / port  
- Certificate + key paths (HTTPS when both set)  
- Web base path (URL prefix)

Env values bootstrap defaults; the UI writes SQLite on the `./config` volume and restarts the process (`restart: unless-stopped`). Keep `WEB_PORT` and Compose port mapping in sync. Ensure `./config` is writable by container uid `10001`.

---

## Security notes

- Keep `ALLOW_WRITE_ACTIONS=false` unless you intentionally enable write APIs toward 3x-ui
- Never commit `.env`, `servers.yaml`, or real API tokens
- Prefer TLS (panel cert settings or a reverse proxy)
- `verify_tls: true` when talking to panels (default)

**Before you push to a public repo:** rotate any token that ever lived in `servers.yaml` / git history, and confirm secrets are gitignored.

---

## Development

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest -q

# Frontend
cd frontend
npm install
npm run dev
```

Docker image builds the Vite app into the FastAPI static dir. If PyPI is flaky during image build, pre-download wheels (optional):

```bash
pip download -r backend/requirements.txt -d backend/wheels
docker compose build --no-cache
```

An empty `backend/wheels/` directory is enough for a normal online build.

---

## Stack

| Layer | Tech |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic |
| DB | PostgreSQL 16 (traffic) · SQLite (panel settings) |
| UI | React, Vite, TanStack Query, Recharts, Tailwind |
| Run | Docker Compose, Uvicorn |

---

## Project layout

```
├── backend/          # FastAPI app, poller, Alembic
├── frontend/         # React dashboard
├── config/           # Mount point: servers.yaml, panel.db, certs
├── docker-compose.yml
├── .env.example
└── servers.yaml.example
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

This project is an independent companion for 3x-ui. It is not affiliated with or endorsed by the 3x-ui authors. Use at your own risk; protect your API tokens and panel URLs.
