from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import users as users_api
from app.config import Settings, get_settings
from app.db import get_db
from app.models import ClientCurrent, Server
from app.security import AuthUser, get_current_user


@pytest.mark.asyncio
async def test_usage_sort_uses_byte_totals(db_engine):
    """500 MiB must sort below 2 GiB when ordering by used ascending (raw bytes, not display units)."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        server = Server(name="main", base_url="http://x", web_base_path="/", source_mode="api")
        session.add(server)
        await session.flush()
        session.add(
            ClientCurrent(
                server_id=server.id,
                email="small@x",
                enable=True,
                up=500 * 1024 * 1024,
                down=0,
                total=0,
                expiry_time=0,
                reset_count=0,
                last_online=0,
            )
        )
        session.add(
            ClientCurrent(
                server_id=server.id,
                email="big@x",
                enable=True,
                up=2 * 1024 * 1024 * 1024,
                down=0,
                total=0,
                expiry_time=0,
                reset_count=0,
                last_online=0,
            )
        )
        session.add(
            ClientCurrent(
                server_id=server.id,
                email="huge@x",
                enable=True,
                up=10 * 1024 * 1024 * 1024,
                down=0,
                total=0,
                expiry_time=0,
                reset_count=0,
                last_online=0,
            )
        )
        await session.commit()

    async def override_db():
        async with factory() as session:
            yield session

    app = FastAPI()
    app.include_router(users_api.router)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(username="admin", role="admin")
    app.dependency_overrides[get_settings] = lambda: Settings(
        tz="UTC", database_url="sqlite+aiosqlite:///:memory:"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/users", params={"sort": "used", "order": "asc"})
        assert r.status_code == 200
        emails = [i["email"] for i in r.json()["items"]]
        assert emails == ["small@x", "big@x", "huge@x"]

        r2 = await client.get("/api/users", params={"sort": "used", "order": "desc"})
        assert [i["email"] for i in r2.json()["items"]] == ["huge@x", "big@x", "small@x"]
