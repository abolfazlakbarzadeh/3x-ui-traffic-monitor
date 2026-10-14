from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import auth
from app.config import Settings, get_settings
from app.security import hash_password


@pytest.mark.asyncio
async def test_login_and_me(monkeypatch):
    get_settings.cache_clear()
    settings = Settings(
        admin_username="admin",
        admin_password_hash=hash_password("adminpass"),
        admin_password="",
        jwt_secret="test-secret",
    )

    def _settings() -> Settings:
        return settings

    monkeypatch.setattr("app.config.get_settings", _settings)
    monkeypatch.setattr("app.api.auth.get_settings", _settings)
    monkeypatch.setattr("app.security.get_settings", _settings)

    test_app = FastAPI()
    test_app.include_router(auth.router)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
        assert bad.status_code == 401
        login = await client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
        assert login.status_code == 200
        assert login.json()["role"] == "admin"
        me = await client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == "admin"

        csrf = login.json()["csrf_token"]
        denied = await client.post("/api/auth/logout")
        assert denied.status_code == 403
        still = await client.get("/api/auth/me")
        assert still.status_code == 200

        out = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert out.status_code == 200
        gone = await client.get("/api/auth/me")
        assert gone.status_code == 401


def test_write_endpoints_not_in_source_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "sources"
    text = "\n".join(p.read_text(encoding="utf-8") for p in root.glob("*.py"))
    for forbidden in (
        "resetTraffic",
        "bulkResetTraffic",
        "resetAllTraffics",
        "updateTraffic",
    ):
        assert forbidden not in text
