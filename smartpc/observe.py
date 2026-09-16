from .db import DB
from .learning import Baseline
from .monitor import snapshot


def observe_once(data_dir):
    """Capture the complete local telemetry at startup in read-only mode."""
    current = snapshot()
    db = DB(data_dir / "smartpc.db")
    db.snapshot(current)
    history = db.recent_snapshots(30)
    return {
        "mode": "observe_only",
        "snapshot": current,
        "baseline": Baseline(history[:-1]).summary(),
    }
