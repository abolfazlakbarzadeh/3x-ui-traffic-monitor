from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.delta import SnapshotCounters, compute_delta
from app.models import CounterReset, RawSnapshot, Server, UsageHourly
from app.schemas import TopUser, UsagePoint, UsageSeries
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api", tags=["usage"])

# Below this span, prefer poll snapshots so minute windows aren't empty /
# mis-attributed to a full hour bucket.
_SNAPSHOT_SPAN = timedelta(hours=3)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _floor_hour(dt: datetime) -> datetime:
    dt = _aware(dt)
    return dt.replace(minute=0, second=0, microsecond=0)


@router.get("/users/{server_id}/{email}/usage", response_model=UsageSeries)
async def user_usage(
    server_id: int,
    email: str,
    granularity: str = Query("hour", pattern="^(hour|day|month)$"),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UsageSeries:
    now = datetime.now(UTC)
    if granularity == "hour":
        start = _aware(from_ts or (now - timedelta(hours=48)))
        end = _aware(to_ts or now)
    elif granularity == "day":
        start = _aware(from_ts or (now - timedelta(days=90)))
        end = _aware(to_ts or now)
    else:
        start = _aware(from_ts or (now - timedelta(days=365)))
        end = _aware(to_ts or now)

    if end < start:
        start, end = end, start

    span = end - start
    use_snapshots = granularity == "hour" and span <= _SNAPSHOT_SPAN

    if use_snapshots:
        points = await _points_from_snapshots(db, server_id, email, start, end)
    else:
        points = await _points_from_hourly(
            db, server_id, email, start, end, granularity, settings.tz
        )

    resets = (
        await db.scalars(
            select(CounterReset)
            .where(
                CounterReset.server_id == server_id,
                CounterReset.email == email,
                CounterReset.ts >= start,
                CounterReset.ts < end,
            )
            .order_by(CounterReset.ts)
        )
    ).all()

    return UsageSeries(
        email=email,
        server_id=server_id,
        granularity=granularity,
        points=points,
        resets=[
            {
                "ts": r.ts.isoformat(),
                "reason": r.reason,
                "prev_up": r.prev_up,
                "prev_down": r.prev_down,
                "cur_up": r.cur_up,
                "cur_down": r.cur_down,
            }
            for r in resets
        ],
    )


async def _points_from_hourly(
    db: AsyncSession,
    server_id: int,
    email: str,
    start: datetime,
    end: datetime,
    granularity: str,
    tz_name: str,
) -> list[UsagePoint]:
    # Include any hour bucket that overlaps [start, end).
    query_start = _floor_hour(start)
    rows = (
        await db.execute(
            select(UsageHourly.hour_start, UsageHourly.up, UsageHourly.down)
            .where(
                UsageHourly.server_id == server_id,
                UsageHourly.email == email,
                UsageHourly.hour_start >= query_start,
                UsageHourly.hour_start < end,
            )
            .order_by(UsageHourly.hour_start)
        )
    ).all()

    tz = ZoneInfo(tz_name)
    buckets: dict[datetime, tuple[int, int]] = {}
    for hour_start, up, down in rows:
        hs = _aware(hour_start)
        # Skip buckets that end at/before start (no overlap)
        if hs + timedelta(hours=1) <= start:
            continue
        local = hs.astimezone(tz)
        if granularity == "hour":
            key = hs
        elif granularity == "day":
            key = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        else:
            key = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        prev = buckets.get(key, (0, 0))
        buckets[key] = (prev[0] + int(up), prev[1] + int(down))

    return [
        UsagePoint(bucket_start=k, up=v[0], down=v[1])
        for k, v in sorted(buckets.items(), key=lambda x: x[0])
    ]


async def _points_from_snapshots(
    db: AsyncSession,
    server_id: int,
    email: str,
    start: datetime,
    end: datetime,
) -> list[UsagePoint]:
    """Build per-poll delta points inside [start, end) from raw cumulative snapshots."""
    baseline = await db.scalar(
        select(RawSnapshot)
        .where(
            RawSnapshot.server_id == server_id,
            RawSnapshot.email == email,
            RawSnapshot.ts <= start,
        )
        .order_by(RawSnapshot.ts.desc())
        .limit(1)
    )
    inside = (
        await db.scalars(
            select(RawSnapshot)
            .where(
                RawSnapshot.server_id == server_id,
                RawSnapshot.email == email,
                RawSnapshot.ts > start,
                RawSnapshot.ts <= end,
            )
            .order_by(RawSnapshot.ts.asc())
        )
    ).all()

    snaps: list[RawSnapshot] = []
    if baseline is not None:
        snaps.append(baseline)
    snaps.extend(inside)
    if len(snaps) < 2:
        return []

    points: list[UsagePoint] = []
    for prev, cur in zip(snaps, snaps[1:]):
        # Only attribute deltas whose interval ends inside the window
        if _aware(cur.ts) <= start or _aware(cur.ts) > end:
            continue
        result = compute_delta(
            SnapshotCounters(
                up=prev.up,
                down=prev.down,
                reset_count=prev.reset_count,
                client_id=prev.client_id,
            ),
            SnapshotCounters(
                up=cur.up,
                down=cur.down,
                reset_count=cur.reset_count,
                client_id=cur.client_id,
            ),
            interval_seconds=max(1, int((_aware(cur.ts) - _aware(prev.ts)).total_seconds())),
            max_sane_bytes_per_sec=125_000_000,
        )
        if result.is_baseline:
            continue
        if result.up or result.down:
            points.append(
                UsagePoint(
                    bucket_start=_aware(cur.ts),
                    up=result.up,
                    down=result.down,
                )
            )
    return points


@router.get("/usage/top", response_model=list[TopUser])
async def top_usage(
    period: str = Query("day", pattern="^(day|month)$"),
    limit: int = Query(10, ge=1, le=100),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[TopUser]:
    now = datetime.now(UTC)
    if from_ts is not None or to_ts is not None:
        start_utc = _aware(from_ts or (now - timedelta(hours=48)))
        end_utc = _aware(to_ts or now)
        if end_utc < start_utc:
            start_utc, end_utc = end_utc, start_utc
    else:
        tz = ZoneInfo(settings.tz)
        local_now = now.astimezone(tz)
        if period == "day":
            start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_utc = start.astimezone(UTC)
        end_utc = now

    # Short windows (e.g. Last 5 minutes) must not rely on hour buckets alone —
    # a window inside the current hour would miss prior-hour rows until N crosses
    # the hour boundary (the "works at ~18" effect).
    if end_utc - start_utc <= _SNAPSHOT_SPAN:
        return await _top_from_snapshots(db, start_utc, end_utc, limit)

    query_start = _floor_hour(start_utc)
    rows = (
        await db.execute(
            select(
                UsageHourly.server_id,
                Server.name,
                UsageHourly.email,
                func.sum(UsageHourly.up).label("up"),
                func.sum(UsageHourly.down).label("down"),
            )
            .join(Server, Server.id == UsageHourly.server_id)
            .where(
                UsageHourly.hour_start >= query_start,
                UsageHourly.hour_start < end_utc,
            )
            .group_by(UsageHourly.server_id, Server.name, UsageHourly.email)
            .order_by(func.sum(UsageHourly.up + UsageHourly.down).desc())
            .limit(limit)
        )
    ).all()
    return [
        TopUser(
            server_id=server_id,
            server_name=server_name,
            email=email,
            up=int(up or 0),
            down=int(down or 0),
            total=int((up or 0) + (down or 0)),
        )
        for server_id, server_name, email, up, down in rows
    ]


async def _top_from_snapshots(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    limit: int,
) -> list[TopUser]:
    """Rank clients by reset-aware deltas inside [start, end] from raw snapshots."""
    start = _aware(start)
    end = _aware(end)
    lookback = start - timedelta(hours=6)

    snaps = (
        await db.scalars(
            select(RawSnapshot)
            .where(RawSnapshot.ts >= lookback, RawSnapshot.ts <= end)
            .order_by(RawSnapshot.server_id, RawSnapshot.email, RawSnapshot.ts)
        )
    ).all()
    if not snaps:
        return []

    from collections import defaultdict

    by_key: dict[tuple[int, str], list[RawSnapshot]] = defaultdict(list)
    for snap in snaps:
        by_key[(snap.server_id, snap.email)].append(snap)

    totals: dict[tuple[int, str], tuple[int, int]] = {}
    for key, series in by_key.items():
        up = down = 0
        prev: RawSnapshot | None = None
        for snap in series:
            ts = _aware(snap.ts)
            if ts <= start:
                prev = snap
                continue
            if ts > end:
                break
            if prev is None:
                prev = snap
                continue
            result = compute_delta(
                SnapshotCounters(
                    up=prev.up,
                    down=prev.down,
                    reset_count=prev.reset_count,
                    client_id=prev.client_id,
                ),
                SnapshotCounters(
                    up=snap.up,
                    down=snap.down,
                    reset_count=snap.reset_count,
                    client_id=snap.client_id,
                ),
                interval_seconds=max(1, int((ts - _aware(prev.ts)).total_seconds())),
                max_sane_bytes_per_sec=125_000_000,
            )
            prev = snap
            if result.is_baseline:
                continue
            up += result.up
            down += result.down
        if up or down:
            totals[key] = (up, down)

    if not totals:
        return []

    server_ids = {sid for sid, _ in totals}
    servers = {
        s.id: s.name
        for s in (
            await db.scalars(select(Server).where(Server.id.in_(server_ids)))
        ).all()
    }

    ranked = sorted(totals.items(), key=lambda kv: kv[1][0] + kv[1][1], reverse=True)[:limit]
    return [
        TopUser(
            server_id=server_id,
            server_name=servers.get(server_id, str(server_id)),
            email=email,
            up=up,
            down=down,
            total=up + down,
        )
        for (server_id, email), (up, down) in ranked
    ]
