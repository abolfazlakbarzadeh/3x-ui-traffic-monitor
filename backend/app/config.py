from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TokenAuth(BaseModel):
    type: Literal["token"] = "token"
    token: str


class PasswordAuth(BaseModel):
    type: Literal["password"] = "password"
    username: str
    password: str
    totp_secret: str | None = None


class ServerConfig(BaseModel):
    name: str
    base_url: str
    web_base_path: str = "/"
    auth: TokenAuth | PasswordAuth
    verify_tls: bool = True
    source_mode: Literal["api", "sqlite"] = "api"
    sqlite_path: str | None = None


def _read_secret_file(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8").strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://xui:xui@db:5432/xui_monitor"
    poll_interval_seconds: int = 60
    online_poll_seconds: int = 30
    tz: str = "Asia/Tehran"
    raw_retention_days: int = 14
    hourly_retention_days: int = 400
    max_sane_bytes_per_sec: int = 125_000_000  # ~1 Gbps
    allow_write_actions: bool = False

    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_password: str = ""  # bootstrap only; hashed at runtime if hash empty
    jwt_secret: str = "change-me"
    session_ttl_hours: int = 24

    viewer_username: str | None = None
    viewer_password_hash: str | None = None
    viewer_password: str | None = None

    xui_servers: str = "[]"
    servers_yaml: str | None = None
    static_dir: str = "/app/frontend/dist"

    jwt_secret_file: str | None = None
    admin_password_file: str | None = None

    def resolved_jwt_secret(self) -> str:
        return _read_secret_file(self.jwt_secret_file) or self.jwt_secret

    def load_servers(self) -> list[ServerConfig]:
        if self.servers_yaml:
            path = Path(self.servers_yaml)
            if path.exists():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
                return [ServerConfig.model_validate(item) for item in data]
        raw = self.xui_servers.strip() or "[]"
        data = json.loads(raw)
        return [ServerConfig.model_validate(item) for item in data]


@lru_cache
def get_settings() -> Settings:
    return Settings()
