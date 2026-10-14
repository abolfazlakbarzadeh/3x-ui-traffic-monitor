from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import ServerConfig, Settings, TokenAuth
from app.models import ClientCurrent, CounterReset, RawSnapshot, Server, UsageHourly
from app.poller import Poller
from app.sources.xui_api import XuiApiSource
from mock_xui import create_mock_panel, sample_client


async def _attach_source(poller: Poller, name: str, app, token: str = "t") -> None:
    transport = ASGITransport(app=app)
    source = XuiApiSource(
        ServerConfig(name=name, base_url="http://test", auth=TokenAuth(token=token))
    )
    source._client = AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    poller._sources[name] = source


@pytest.mark.asyncio
async def test_two_servers_ingest(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", poll_interval_seconds=60)
    poller = Poller(settings=settings)

    # Patch SessionLocal used by poller
    import app.poller as poller_mod
    import app.db as db_mod

    db_mod.SessionLocal = factory
    poller_mod.SessionLocal = factory

    async with factory() as session:
        s1 = Server(name="a", base_url="http://a", web_base_path="/", source_mode="api")
        s2 = Server(name="b", base_url="http://b", web_base_path="/", source_mode="api")
        session.add_all([s1, s2])
        await session.commit()
        await session.refresh(s1)
        await session.refresh(s2)
        poller._server_ids = {"a": s1.id, "b": s2.id}

    app_a = create_mock_panel(clients=[sample_client("u1@x", up=100, down=0)], token="t")
    app_b = create_mock_panel(clients=[sample_client("u2@x", up=0, down=50)], token="t")
    await _attach_source(poller, "a", app_a)
    await _attach_source(poller, "b", app_b)

    await poller.poll_traffic_once()

    # second poll with growth
    app_a.state["clients"] = [sample_client("u1@x", up=150, down=10)]
    app_b.state["clients"] = [sample_client("u2@x", up=20, down=80)]
    await poller.poll_traffic_once()

    async with factory() as session:
        snaps = (await session.scalars(select(RawSnapshot))).all()
        assert len(snaps) >= 4
        usage = (await session.scalars(select(UsageHourly))).all()
        assert usage
        totals = {(u.email, u.up, u.down) for u in usage}
        assert any(e == "u1@x" and up == 50 and down == 10 for e, up, down in ((u.email, u.up, u.down) for u in usage))
        clients = (await session.scalars(select(ClientCurrent))).all()
        assert {c.email for c in clients} == {"u1@x", "u2@x"}

    for s in poller._sources.values():
        await s.close()


@pytest.mark.asyncio
async def test_reset_records_event(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    import app.poller as poller_mod

    poller_mod.SessionLocal = factory
    settings = Settings(poll_interval_seconds=60)
    poller = Poller(settings=settings)

    async with factory() as session:
        s = Server(name="a", base_url="http://a", web_base_path="/", source_mode="api")
        session.add(s)
        await session.commit()
        await session.refresh(s)
        poller._server_ids = {"a": s.id}

    app = create_mock_panel(clients=[sample_client("r@x", up=1000, down=500, client_id=1)], token="t")
    await _attach_source(poller, "a", app)
    await poller.poll_traffic_once()
    app.state["clients"] = [sample_client("r@x", up=5, down=5, client_id=1)]
    await poller.poll_traffic_once()

    async with factory() as session:
        resets = (await session.scalars(select(CounterReset))).all()
        assert len(resets) == 1
        assert resets[0].reason == "counter_decreased"
        usage = (await session.scalars(select(UsageHourly))).all()
        assert any(u.up == 5 and u.down == 5 for u in usage)

    await poller._sources["a"].close()
