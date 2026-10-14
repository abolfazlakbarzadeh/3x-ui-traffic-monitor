from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SnapshotCounters:
    up: int
    down: int
    reset_count: int = 0
    client_id: int | None = None


@dataclass(frozen=True)
class DeltaResult:
    up: int
    down: int
    is_baseline: bool = False
    is_reset: bool = False
    reset_reason: str | None = None
    is_anomaly: bool = False


def compute_delta(
    prev: SnapshotCounters | None,
    cur: SnapshotCounters,
    *,
    interval_seconds: int,
    max_sane_bytes_per_sec: int,
) -> DeltaResult:
    """Compute traffic delta between two cumulative snapshots.

    Rules:
    - First snapshot (prev is None) → baseline, delta 0
    - Reset if cur < prev (up or down), reset_count increased, or client_id changed
      → delta = cur (traffic since reset)
    - Otherwise delta = cur - prev, clamped to >= 0
    - Flag anomaly when delta exceeds max_sane_bytes_per_sec * interval
    """
    if prev is None:
        return DeltaResult(up=0, down=0, is_baseline=True)

    reset_reason: str | None = None
    if cur.client_id is not None and prev.client_id is not None and cur.client_id != prev.client_id:
        reset_reason = "client_recreated"
    elif cur.reset_count > prev.reset_count:
        reset_reason = "reset_count"
    elif cur.up < prev.up or cur.down < prev.down:
        reset_reason = "counter_decreased"

    if reset_reason:
        up = max(0, cur.up)
        down = max(0, cur.down)
        anomaly = _is_anomaly(up, down, interval_seconds, max_sane_bytes_per_sec)
        return DeltaResult(
            up=up,
            down=down,
            is_reset=True,
            reset_reason=reset_reason,
            is_anomaly=anomaly,
        )

    up = max(0, cur.up - prev.up)
    down = max(0, cur.down - prev.down)
    anomaly = _is_anomaly(up, down, interval_seconds, max_sane_bytes_per_sec)
    return DeltaResult(up=up, down=down, is_anomaly=anomaly)


def _is_anomaly(up: int, down: int, interval_seconds: int, max_sane: int) -> bool:
    if interval_seconds <= 0:
        return False
    ceiling = max_sane * interval_seconds
    return (up + down) > ceiling
