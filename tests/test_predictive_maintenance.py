import datetime as dt
from pathlib import Path

from smartpc.config import Settings
from smartpc.engine import Engine
from smartpc.models import SystemSnapshot


def _ts(hours_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours_ago)).isoformat()


def _snap(hours_ago: float, free_gb: float) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=_ts(hours_ago),
        cpu_percent=10,
        ram_percent=30,
        disk_percent=70,
        disk_free_gb=free_gb,
        process_count=50,
        boot_seconds=100,
        top_processes=[],
    )


def _engine(tmp_path: Path) -> Engine:
    return Engine(data_dir=tmp_path)


def test_predicts_threshold_breach_from_measured_growth(tmp_path):
    engine = _engine(tmp_path)
    current = _snap(0, 30)
    history = [_snap(24 - i * 4, 30 + i * 4) for i in range(6)]
    result = engine._predict_disk_pressure(history, current)
    assert result["enabled"] is True
    assert result["samples"] >= 6
    assert result["rate_gb_per_hour"] > 0.25
    assert result["triggered"] is True


def test_does_not_predict_with_insufficient_history(tmp_path):
    engine = _engine(tmp_path)
    result = engine._predict_disk_pressure([_snap(2, 31), _snap(1, 30.8)], _snap(0, 30.5))
    assert result["triggered"] is False
    assert result["reason"] == "insufficient historical samples"


def test_noise_floor_prevents_false_trigger(tmp_path):
    engine = _engine(tmp_path)
    current = _snap(0, 30)
    history = [_snap(24 - i * 4, 30 + i * 0.1) for i in range(6)]
    result = engine._predict_disk_pressure(history, current)
    assert result["triggered"] is False
    assert result["rate_gb_per_hour"] < 0.25
