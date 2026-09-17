import datetime as dt
import os
import time

import psutil

from .models import SystemSnapshot


def _disk_root() -> str:
    return os.environ.get("SystemDrive", "C:") + "\\"


def _load_average() -> float | None:
    """Return the first load-average value when Windows exposes it.

    Some Windows installations have disabled/broken Performance Data Helper
    counters. psutil.getloadavg() raises RuntimeError in that case. Load average
    is supplementary telemetry, so failure must never abort a full inspection.
    We deliberately return None rather than manufacturing a replacement value.
    """
    try:
        return float(psutil.getloadavg()[0])
    except (AttributeError, OSError, RuntimeError, psutil.Error):
        return None


def snapshot(interval: float = 0.10, process_limit: int = 10) -> SystemSnapshot:
    """Collect a bounded local snapshot; avoid long sampling intervals."""
    cpu = psutil.cpu_percent(interval=max(0.0, min(float(interval), 1.0)))
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(_disk_root())
    boot = time.time() - psutil.boot_time()
    net = psutil.net_io_counters()
    rows = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            i = p.info
            rows.append({
                "pid": i["pid"],
                "name": i.get("name") or "",
                "cpu": float(i.get("cpu_percent") or 0),
                "memory": float(i.get("memory_percent") or 0),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    rows.sort(key=lambda x: (x["memory"], x["cpu"]), reverse=True)
    return SystemSnapshot(
        dt.datetime.now(dt.timezone.utc).isoformat(), cpu, vm.percent,
        disk.percent, disk.free / 1024**3, len(rows), boot,
        rows[:max(0, int(process_limit))], _load_average(),
        net.bytes_sent if net else 0, net.bytes_recv if net else 0,
    )


def snapshot_fast() -> SystemSnapshot:
    """Low-overhead snapshot for scheduled maintenance/startup observation.

    It intentionally avoids per-process enumeration because unattended maintenance
    only needs CPU/RAM/disk/network counters and must return quickly.
    """
    cpu = psutil.cpu_percent(interval=0.0)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(_disk_root())
    boot = time.time() - psutil.boot_time()
    net = psutil.net_io_counters()
    try:
        process_count = len(psutil.pids())
    except (OSError, psutil.Error):
        process_count = 0
    return SystemSnapshot(
        dt.datetime.now(dt.timezone.utc).isoformat(), cpu, vm.percent,
        disk.percent, disk.free / 1024**3, process_count, boot, [], _load_average(),
        net.bytes_sent if net else 0, net.bytes_recv if net else 0,
    )
