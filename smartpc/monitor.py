import datetime as dt
import os
import time
import psutil
from .models import SystemSnapshot

def snapshot() -> SystemSnapshot:
    cpu = psutil.cpu_percent(interval=0.35)
    vm = psutil.virtual_memory()
    root = os.environ.get("SystemDrive", "C:") + "\\"
    disk = psutil.disk_usage(root)
    boot = time.time() - psutil.boot_time()
    rows=[]
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent"]):
        try:
            i=p.info
            rows.append({"pid":i["pid"],"name":i.get("name") or "", "cpu":i.get("cpu_percent") or 0.0,"memory":i.get("memory_percent") or 0.0})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    rows.sort(key=lambda x:(x["memory"],x["cpu"]), reverse=True)
    return SystemSnapshot(dt.datetime.now(dt.timezone.utc).isoformat(), cpu, vm.percent, disk.percent, disk.free/1024**3, len(rows), boot, rows[:10])
