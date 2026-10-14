from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Server, UsageHourly


@pytest.mark.asyncio
async def test_daily_equals_sum_of_hourly(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    tz = ZoneInfo("Asia/Tehran")
    day = datetime(2026, 3, 20, 0, 0, tzinfo=tz)
    async with factory() as session:
        server = Server(name="s", base_url="http://x", web_base_path="/", source_mode="api")
        session.add(server)
        await session.flush()
        total_up = 0
        total_down = 0
        for h in range(24):
            hour = (day + timedelta(hours=h)).astimezone(UTC)
            up, down = h + 1, h * 2
            total_up += up
            total_down += down
            session.add(
                UsageHourly(
                    server_id=server.id,
                    email="agg@x",
                    hour_start=hour,
                    up=up,
                    down=down,
                )
            )
        await session.commit()

        start = day.astimezone(UTC)
        end = (day + timedelta(days=1)).astimezone(UTC)
        from sqlalchemy import func, select

        row = (
            await session.execute(
                select(func.sum(UsageHourly.up), func.sum(UsageHourly.down)).where(
                    UsageHourly.email == "agg@x",
                    UsageHourly.hour_start >= start,
                    UsageHourly.hour_start < end,
                )
            )
        ).one()
        assert int(row[0]) == total_up
        assert int(row[1]) == total_down
