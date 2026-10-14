# Panel Settings (listen / domain / port / TLS)

**Status:** approved for implementation (hybrid approach)  
**Date:** 2026-10-14

## Goal

Configure **this** traffic monitor like 3x-ui Panel Settings → General: listen IP, domain, port, cert/key paths, and web base path.

## Decisions

- Env / `.env` bootstraps defaults; Settings UI overrides at runtime.
- Overrides live in **SQLite** (`PANEL_SETTINGS_DB`, default `/config/panel.db`) — separate from Postgres traffic data.
- Save writes SQLite then exits the process so Docker restarts with the new bind.
- Admin-only Settings UI.
- Compose must publish the chosen `webPort` (document + UI warning).

## Fields

| Key | Meaning |
| --- | --- |
| `webListen` | Bind IP (empty = all interfaces) |
| `webDomain` | Exact Host allowlist (empty = allow all) |
| `webPort` | Listen port (default 8000) |
| `webCertFile` / `webKeyFile` | TLS paths; both set → HTTPS |
| `webBasePath` | URL prefix for SPA + API |

## Merge order

`env defaults` → `SQLite row` (non-null overrides) → effective config at process start.
