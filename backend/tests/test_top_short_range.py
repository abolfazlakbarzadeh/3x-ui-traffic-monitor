from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.usage import _top_from_snapshots
from app.models import RawSnapshot, Server, UsageHourly


@pytest.mark.asyncio
async def test_top_short_minutes_uses_snapshots_not_hour_boundary(db_engine):
    """Last ~5 minutes must return deltas even when only the current hour has no hourly row
    and prior-hour occupancy would only appear after crossing the hour mark."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        server = Server(name="s", base_url="http://x", web_base_path="/", source_mode="api")
        session.add(server)
        await session.flush()

        # Previous hour has a big hourly bucket (would dominate a buggy hour-boundary query)
        prev_hour = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
        session.add(
            UsageHourly(
                server_id=server.id,
                email="old@x",
                hour_start=prev_hour,
                up=9_000_000,
                down=0,
            )
        )

        # Now is 08:17 — last 5 minutes is 08:12–08:17 (still inside 08:00 hour)
        now = datetime(2026, 10, 14, 8, 17, tzinfo=UTC)
        start = now - timedelta(minutes=5)
        # Poll snapshots inside the 5-minute window
        base = now - timedelta(minutes=6)
        session.add(
            RawSnapshot(
                server_id=server.id,
                email="hot@x",
                ts=base,
                up=100,
                down=0,
                total=0,
                expiry_time=0,
                enable=True,
                reset_count=0,
                client_id=1,
                last_online=0,
            )
        )
        session.add(
            RawSnapshot(
                server_id=server.id,
                email="hot@x",
                ts=now - timedelta(minutes=2),
                up=100 + 50_000,
                down=10_000,
                total=0,
                expiry_time=0,
                enable=True,
                reset_count=0,
                client_id=1,
                last_online=0,
            )
        )
        await session.commit()

        top = await _top_from_snapshots(session, start, now, limit=10)
        assert len(top) == 1
        assert top[0].email == "hot@x"
        assert top[0].up == 50_000
        assert top[0].down == 10_000
