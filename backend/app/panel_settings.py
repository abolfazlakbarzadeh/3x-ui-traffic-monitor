"""Panel listen/TLS settings: env defaults merged with SQLite overrides."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import Settings


@dataclass
class PanelSettings:
    web_listen: str = ""
    web_domain: str = ""
    web_port: int = 8000
    web_cert_file: str = ""
    web_key_file: str = ""
    web_base_path: str = "/"

    def normalized_base_path(self) -> str:
        path = (self.web_base_path or "/").strip() or "/"
        if path != "/" and not path.startswith("/"):
            path = "/" + path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path or "/"

    def tls_enabled(self) -> bool:
        return bool(self.web_cert_file and self.web_key_file)

    def to_public_dict(self) -> dict:
        return {
            "web_listen": self.web_listen,
            "web_domain": self.web_domain,
            "web_port": self.web_port,
            "web_cert_file": self.web_cert_file,
            "web_key_file": self.web_key_file,
            "web_base_path": self.normalized_base_path(),
            "tls_enabled": self.tls_enabled(),
        }


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS panel_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    web_listen TEXT NOT NULL DEFAULT '',
    web_domain TEXT NOT NULL DEFAULT '',
    web_port INTEGER NOT NULL DEFAULT 8000,
    web_cert_file TEXT NOT NULL DEFAULT '',
    web_key_file TEXT NOT NULL DEFAULT '',
    web_base_path TEXT NOT NULL DEFAULT '/'
);
"""


def panel_db_path(settings: Settings | None = None) -> Path:
    from app.config import get_settings

    s = settings or get_settings()
    return Path(s.panel_settings_db)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_SQL)
    conn.commit()
    return conn


def defaults_from_env(settings: Settings) -> PanelSettings:
    return PanelSettings(
        web_listen=settings.web_listen,
        web_domain=settings.web_domain,
        web_port=settings.web_port,
        web_cert_file=settings.web_cert_file,
        web_key_file=settings.web_key_file,
        web_base_path=settings.web_base_path,
    )


def load_overrides(db_path: Path) -> PanelSettings | None:
    if not db_path.exists():
        return None
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM panel_settings WHERE id = 1").fetchone()
        if not row:
            return None
        return PanelSettings(
            web_listen=row["web_listen"] or "",
            web_domain=row["web_domain"] or "",
            web_port=int(row["web_port"] or 8000),
            web_cert_file=row["web_cert_file"] or "",
            web_key_file=row["web_key_file"] or "",
            web_base_path=row["web_base_path"] or "/",
        )


def merge_panel_settings(settings: Settings | None = None) -> PanelSettings:
    from app.config import get_settings

    s = settings or get_settings()
    base = defaults_from_env(s)
    overrides = load_overrides(panel_db_path(s))
    if not overrides:
        return base
    # SQLite row is full snapshot of last save (not sparse nulls).
    return overrides


def save_panel_settings(panel: PanelSettings, settings: Settings | None = None) -> PanelSettings:
    from app.config import get_settings

    s = settings or get_settings()
    if panel.web_port < 1 or panel.web_port > 65535:
        raise ValueError("web_port must be between 1 and 65535")
    path = panel.normalized_base_path()
    panel.web_base_path = path
    if panel.web_listen.strip():
        # Basic sanity: reject spaces; full IP validation left to bind time.
        if " " in panel.web_listen.strip():
            raise ValueError("web_listen is not a valid address")

    db_path = panel_db_path(s)
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO panel_settings (
                id, web_listen, web_domain, web_port, web_cert_file, web_key_file, web_base_path
            ) VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                web_listen = excluded.web_listen,
                web_domain = excluded.web_domain,
                web_port = excluded.web_port,
                web_cert_file = excluded.web_cert_file,
                web_key_file = excluded.web_key_file,
                web_base_path = excluded.web_base_path
            """,
            (
                panel.web_listen.strip(),
                panel.web_domain.strip(),
                panel.web_port,
                panel.web_cert_file.strip(),
                panel.web_key_file.strip(),
                panel.web_base_path,
            ),
        )
        conn.commit()
    return panel


def panel_settings_as_env(panel: PanelSettings) -> dict[str, str]:
    """Export for entrypoint / debugging."""
    d = asdict(panel)
    return {k.upper(): str(v) for k, v in d.items()}
