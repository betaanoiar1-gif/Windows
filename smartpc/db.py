import json
import sqlite3
import time
from pathlib import Path
from .models import SystemSnapshot


class DB:
    def __init__(self, path="smartpc.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, ts TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, ts TEXT, action TEXT, target TEXT, result TEXT)")
            c.execute("""CREATE TABLE IF NOT EXISTS maintenance_runs(
                id INTEGER PRIMARY KEY,
                started_at REAL NOT NULL,
                finished_at REAL,
                trigger TEXT NOT NULL,
                files_moved INTEGER NOT NULL DEFAULT 0,
                bytes_moved INTEGER NOT NULL DEFAULT 0,
                free_before_gb REAL,
                free_after_gb REAL,
                result TEXT NOT NULL,
                reason TEXT
            )""")
            c.execute("CREATE TABLE IF NOT EXISTS maintenance_lock(id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, locked_until REAL)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(ts)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_started ON maintenance_runs(started_at)")

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

    def try_acquire_maintenance(self, owner: str, lease_seconds: float = 900.0) -> bool:
        """Atomically acquire a short maintenance lease; stale leases expire safely."""
        now = time.time()
        until = now + max(1.0, float(lease_seconds))
        with sqlite3.connect(self.path, timeout=5.0) as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT owner, locked_until FROM maintenance_lock WHERE id=1").fetchone()
            if row and row[1] and float(row[1]) > now and row[0] != owner:
                return False
            c.execute(
                "INSERT INTO maintenance_lock(id,owner,locked_until) VALUES(1,?,?) "
                "ON CONFLICT(id) DO UPDATE SET owner=excluded.owner, locked_until=excluded.locked_until",
                (owner, until),
            )
            return True

    def release_maintenance(self, owner: str):
        with sqlite3.connect(self.path) as c:
            c.execute("DELETE FROM maintenance_lock WHERE id=1 AND owner=?", (owner,))

    def maintenance_run(self, started_at, finished_at, trigger, files_moved, bytes_moved,
                        free_before_gb, free_after_gb, result, reason=None):
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO maintenance_runs(started_at,finished_at,trigger,files_moved,bytes_moved,free_before_gb,free_after_gb,result,reason) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (started_at, finished_at, trigger, int(files_moved), int(bytes_moved), free_before_gb, free_after_gb, result, reason),
            )

    def last_maintenance(self, successful_only=True):
        with sqlite3.connect(self.path) as c:
            if successful_only:
                row = c.execute(
                    "SELECT started_at,finished_at,files_moved,bytes_moved,free_before_gb,free_after_gb,result,reason "
                    "FROM maintenance_runs WHERE bytes_moved > 0 ORDER BY id DESC LIMIT 1"
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT started_at,finished_at,files_moved,bytes_moved,free_before_gb,free_after_gb,result,reason "
                    "FROM maintenance_runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
        return row

    def maintenance_bytes_since(self, since_epoch: float) -> int:
        with sqlite3.connect(self.path) as c:
            row = c.execute(
                "SELECT COALESCE(SUM(bytes_moved),0) FROM maintenance_runs WHERE started_at >= ?",
                (float(since_epoch),),
            ).fetchone()
        return int(row[0] or 0)
