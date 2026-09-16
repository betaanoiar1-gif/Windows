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
    net = psutil.net_io_counters()
    rows = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            i = p.info
            rows.append({"pid": i["pid"], "name": i.get("name") or "", "cpu": float(i.get("cpu_percent") or 0), "memory": float(i.get("memory_percent") or 0)})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    rows.sort(key=lambda x: (x["memory"], x["cpu"]), reverse=True)
    load = None
    try:
        load = float(psutil.getloadavg()[0])
    except (AttributeError, OSError):
        pass
    return SystemSnapshot(dt.datetime.now(dt.timezone.utc).isoformat(), cpu, vm.percent, disk.percent, disk.free / 1024**3, len(rows), boot, rows[:10], load, net.bytes_sent if net else 0, net.bytes_recv if net else 0)
