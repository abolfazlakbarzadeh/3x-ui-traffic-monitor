from app.delta import SnapshotCounters, compute_delta


def test_first_snapshot_baseline():
    cur = SnapshotCounters(up=100, down=50)
    result = compute_delta(None, cur, interval_seconds=60, max_sane_bytes_per_sec=1_000_000)
    assert result.is_baseline
    assert result.up == 0
    assert result.down == 0
    assert not result.is_reset


def test_normal_delta():
    prev = SnapshotCounters(up=100, down=50, reset_count=0, client_id=1)
    cur = SnapshotCounters(up=150, down=80, reset_count=0, client_id=1)
    result = compute_delta(prev, cur, interval_seconds=60, max_sane_bytes_per_sec=1_000_000)
    assert result.up == 50
    assert result.down == 30
    assert not result.is_reset
    assert not result.is_anomaly


def test_counter_decreased_reset():
    prev = SnapshotCounters(up=1000, down=500, reset_count=0, client_id=1)
    cur = SnapshotCounters(up=10, down=5, reset_count=0, client_id=1)
    result = compute_delta(prev, cur, interval_seconds=60, max_sane_bytes_per_sec=1_000_000)
    assert result.is_reset
    assert result.reset_reason == "counter_decreased"
    assert result.up == 10
    assert result.down == 5


def test_reset_count_increment():
    prev = SnapshotCounters(up=100, down=50, reset_count=1, client_id=1)
    cur = SnapshotCounters(up=20, down=10, reset_count=2, client_id=1)
    result = compute_delta(prev, cur, interval_seconds=60, max_sane_bytes_per_sec=1_000_000)
    assert result.is_reset
    assert result.reset_reason == "reset_count"
    assert result.up == 20


def test_client_recreated():
    prev = SnapshotCounters(up=100, down=50, reset_count=0, client_id=1)
    cur = SnapshotCounters(up=5, down=5, reset_count=0, client_id=99)
    result = compute_delta(prev, cur, interval_seconds=60, max_sane_bytes_per_sec=1_000_000)
    assert result.is_reset
    assert result.reset_reason == "client_recreated"


def test_anomaly_flagged_but_kept():
    prev = SnapshotCounters(up=0, down=0, client_id=1)
    cur = SnapshotCounters(up=10_000_000_000, down=0, client_id=1)
    result = compute_delta(prev, cur, interval_seconds=60, max_sane_bytes_per_sec=1000)
    assert result.up == 10_000_000_000
    assert result.is_anomaly
