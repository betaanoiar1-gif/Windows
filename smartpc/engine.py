from pathlib import Path
import datetime as dt
from .monitor import snapshot
from .storage import scan_temp,safe_quarantine
from .safety import authorize_all
from .db import DB

class Engine:
    def __init__(self, data_dir="."):
        self.data=Path(data_dir); self.data.mkdir(parents=True,exist_ok=True); self.db=DB(self.data/"smartpc.db")
    def inspect(self):
        s=snapshot(); self.db.snapshot(s)
        candidates=authorize_all(scan_temp(),auto=False)
        return s,candidates
    def optimize_safe(self):
        before=snapshot(); self.db.snapshot(before)
        candidates=authorize_all(scan_temp(),auto=True)
        moved=safe_quarantine(candidates,self.data/"quarantine")
        ts=dt.datetime.now(dt.timezone.utc).isoformat()
        for src,dst in moved:self.db.action(ts,"quarantine",src,"ok:"+dst)
        after=snapshot(); self.db.snapshot(after)
        return before,after,moved
