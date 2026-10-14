# xui-traffic-monitor

Per-client traffic history (hourly / daily / monthly) for [3x-ui](https://github.com/MHSanaei/3x-ui). The panel only keeps cumulative counters; this monitor polls them, stores reset-aware deltas, and serves a dashboard.

## Quick start

```bash
cp .env.example .env
# edit ADMIN_PASSWORD, JWT_SECRET, and XUI_SERVERS (or servers.yaml)
docker compose up -d --build
```

Open http://localhost:8000 and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

## 3x-ui API token (required)

Create a token under **Settings → Security → API Token**.

**You need an `admin`-scope token.** A `monitor`-scope token only covers server metrics endpoints and **cannot** list clients. The monitor will surface a clear error if the scope is wrong.

Treat the token as a secret. It never leaves the server process and is never sent to the browser.

Example `XUI_SERVERS`:

```json
[
  {
    "name": "main",
    "base_url": "https://panel.example.com:2053",
    "web_base_path": "/secretpath/",
    "verify_tls": true,
    "source_mode": "api",
    "auth": { "type": "token", "token": "YOUR_ADMIN_SCOPE_TOKEN" }
  }
]
```

Or mount `servers.yaml` (see `servers.yaml.example`) and set `SERVERS_YAML=/config/servers.yaml`.

Password auth (`auth.type: password`) is supported as a fallback (CSRF + session cookie). Prefer tokens.

## SQLite read-only mode

When the monitor runs on the same host as 3x-ui:

```yaml
source_mode: sqlite
sqlite_path: /xui/x-ui.db
```

Bind-mount the panel DB read-only, e.g. `/etc/x-ui:/xui:ro`. Online status is not available; “recently active” can be inferred from `last_online`.

## Multi-server

Configure multiple entries in `XUI_SERVERS` / `servers.yaml`. Identity is `(server_id, email)`. The users table can filter by server.

## Retention & backup

| Env | Default | Meaning |
|---|---|---|
| `RAW_RETENTION_DAYS` | 14 | Raw cumulative snapshots |
| `HOURLY_RETENTION_DAYS` | 400 | Hourly delta buckets |
| `TZ` | `Asia/Tehran` | Day/month boundaries |

Back up the Postgres volume (`pgdata`) regularly. The monitor DB is independent of `x-ui.db`.

## Security

- Read-only toward 3x-ui by default (`ALLOW_WRITE_ACTIONS=false`)
- Monitor login: argon2 password hash + JWT in httpOnly cookie + CSRF on POSTs
- Put this app behind a reverse proxy (TLS) in production
- Verify TLS to panels by default (`verify_tls: true`)

## Development

```bash
# backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && pytest -v

# frontend
cd frontend && npm install && npm run dev
```

If Docker builds fail downloading from PyPI, refresh a local wheelhouse first:

```bash
cd backend && pip download -r requirements.txt -d wheels
docker compose build --no-cache
```

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Postgres 16 · React · Vite · TanStack Query · Recharts · Tailwind
