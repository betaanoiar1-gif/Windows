import json
import sqlite3
from pathlib import Path
from .models import SystemSnapshot

class DB:
    def __init__(self, path="smartpc.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, ts TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, ts TEXT, action TEXT, target TEXT, result TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts)")

    def snapshot(self, s: SystemSnapshot):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO snapshots(ts,payload) VALUES(?,?)", (s.timestamp, json.dumps(s.to_dict())))

    def action(self, ts, action, target, result):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO actions(ts,action,target,result) VALUES(?,?,?,?)", (ts, action, target, result))

    def recent_snapshots(self, limit=30) -> list[SystemSnapshot]:
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for (payload,) in reversed(rows):
            try:
                d = json.loads(payload)
                out.append(SystemSnapshot(**d))
            except (TypeError, ValueError, KeyError):
                continue
        return out

    def recent_actions(self, limit=50):
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT ts,action,target,result FROM actions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
