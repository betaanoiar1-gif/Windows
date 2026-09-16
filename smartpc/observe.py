from .db import DB
from .learning import Baseline
from .monitor import snapshot_fast


def observe_once(data_dir):
    """Capture minimal local telemetry for fast, read-only startup learning."""
    current = snapshot_fast()
    db = DB(data_dir / "smartpc.db")
    db.snapshot(current)
    history = db.recent_snapshots(30)
    return {
        "mode": "observe_only",
        "snapshot": current,
        "baseline": Baseline(history[:-1]).summary(),
    }
