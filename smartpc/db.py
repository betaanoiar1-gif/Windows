import json, sqlite3
from pathlib import Path
class DB:
    def __init__(self,path="smartpc.db"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY, ts TEXT, payload TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, ts TEXT, action TEXT, target TEXT, result TEXT)")
    def snapshot(self,s):
        with sqlite3.connect(self.path) as c:c.execute("INSERT INTO snapshots(ts,payload) VALUES(?,?)",(s.timestamp,json.dumps(s.__dict__)))
    def action(self,ts,action,target,result):
        with sqlite3.connect(self.path) as c:c.execute("INSERT INTO actions(ts,action,target,result) VALUES(?,?,?,?)",(ts,action,target,result))
