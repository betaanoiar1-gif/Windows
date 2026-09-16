import datetime as dt
from .ai import AIClient
from .config import Settings
from .db import DB
from .diagnostics import diagnose
from .health import health_score
from .learning import Baseline
from .monitor import snapshot
from .safety import authorize_all
from .storage import safe_quarantine, scan_temp

class Engine:
    def __init__(self, data_dir=None):
        self.settings = Settings.load(data_dir)
        self.data = self.settings.data_dir
        self.data.mkdir(parents=True, exist_ok=True)
        self.db = DB(self.data / "smartpc.db")
        self.ai = AIClient(timeout=self.settings.ai_timeout_seconds)

    def inspect(self, include_ai=True):
        current = snapshot()
        self.db.snapshot(current)
        history = self.db.recent_snapshots(30)
        baseline = Baseline(history[:-1])
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=False)
        diagnoses = diagnose(current, history[:-1])
        payload = {
            "system": current.to_dict(),
            "health_score": health_score(current, diagnoses),
            "baseline": baseline.summary(),
            "diagnoses": [d.to_dict() for d in diagnoses],
            "candidates": [{"candidate_id": str(i), **c.to_dict()} for i, c in enumerate(candidates)]
        }
        ai = self.ai.analyze(payload) if include_ai else {"mode":"disabled","actions":[]}
        return {"snapshot": current, "candidates": candidates, "diagnoses": diagnoses, "health_score": payload["health_score"], "baseline": payload["baseline"], "ai": ai}

    def optimize_safe(self):
        before = snapshot()
        self.db.snapshot(before)
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=True)
        moved = safe_quarantine(candidates, self.data / "quarantine", self.settings.max_quarantine_files)
        ts = dt.datetime.now(dt.timezone.utc).isoformat()
        for src, dst, token in moved:
            self.db.action(ts, "quarantine", src, f"ok:{dst}:{token}")
        after = snapshot()
        self.db.snapshot(after)
        return {"before": before, "after": after, "moved": moved}

    def restore(self, token: str):
        from .storage import restore
        path = restore(self.data / "quarantine", token)
        self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), "restore", path, "ok")
        return path
