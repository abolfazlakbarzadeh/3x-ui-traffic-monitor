from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from app.config import ServerConfig
from app.sources.base import ClientTrafficSnapshot

logger = logging.getLogger(__name__)


class XuiSqliteSource:
    """Read-only SQLite source for same-host deployments."""

    def __init__(self, config: ServerConfig) -> None:
        self.name = config.name
        self.config = config
        if not config.sqlite_path:
            raise ValueError(f"sqlite_path required for server {config.name}")
        self.path = Path(config.sqlite_path)

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self.path}?mode=ro&_busy_timeout=5000"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    async def list_clients(self) -> list[ClientTrafficSnapshot]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, email, up, down, total, enable, expiry_time,
                       COALESCE(reset_count, 0) AS reset_count,
                       COALESCE(last_online, 0) AS last_online
                FROM client_traffics
                """
            ).fetchall()
        return [
            ClientTrafficSnapshot(
                email=row["email"],
                up=int(row["up"] or 0),
                down=int(row["down"] or 0),
                total=int(row["total"] or 0),
                expiry_time=int(row["expiry_time"] or 0),
                enable=bool(row["enable"]),
                reset_count=int(row["reset_count"] or 0),
                client_id=int(row["id"]) if row["id"] is not None else None,
                last_online=int(row["last_online"] or 0),
            )
            for row in rows
        ]

    async def get_onlines(self) -> list[str]:
        # Online API unavailable; treat recent last_online as "recently active" elsewhere.
        return []

    async def get_last_online(self) -> dict[str, int]:
        clients = await self.list_clients()
        return {c.email: c.last_online for c in clients}

    async def get_server_status(self) -> dict[str, Any] | None:
        return {"mode": "sqlite", "path": str(self.path)}

    async def probe_capabilities(self) -> list[str]:
        if not self.path.exists():
            logger.warning("SQLite DB missing for %s: %s", self.name, self.path)
            return ["sqlite_db"]
        return []

    async def close(self) -> None:
        return None
