import os
import platform
import statistics
import psutil
from .models import Diagnosis, Risk, SystemSnapshot


def report() -> dict:
    root = os.environ.get("SystemDrive", "C:") + "\\"
    d = psutil.disk_usage(root)
    vm = psutil.virtual_memory()
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_logical": psutil.cpu_count(),
        "cpu_physical": psutil.cpu_count(logical=False),
        "memory_gb": round(vm.total / 1024**3, 2),
        "disk_total_gb": round(d.total / 1024**3, 2),
        "disk_free_gb": round(d.free / 1024**3, 2),
        "disk_percent": d.percent,
        "boot_time": psutil.boot_time(),
    }


def diagnose(snapshot: SystemSnapshot, baseline: list[SystemSnapshot] | None = None) -> list[Diagnosis]:
    baseline = baseline or []
    out: list[Diagnosis] = []
    if snapshot.ram_percent >= 90:
        out.append(Diagnosis("RAM_HIGH", Risk.MEDIUM, "Very high memory pressure", [f"RAM usage is {snapshot.ram_percent:.1f}%"], ["memory-heavy applications", "too many concurrent processes"], ["close unused applications", "inspect top memory processes"]))
    elif snapshot.ram_percent >= 80:
        out.append(Diagnosis("RAM_ELEVATED", Risk.LOW, "Elevated memory usage", [f"RAM usage is {snapshot.ram_percent:.1f}%"], ["normal workload or background applications"], ["inspect top processes"]))
    if snapshot.cpu_percent >= 90:
        out.append(Diagnosis("CPU_HIGH", Risk.MEDIUM, "High CPU utilization", [f"CPU usage is {snapshot.cpu_percent:.1f}%"], ["active workload", "background process", "system task"], ["inspect top CPU processes"]))
    if snapshot.disk_percent >= 90:
        out.append(Diagnosis("DISK_FULL", Risk.MEDIUM, "Low free system-disk capacity", [f"Disk is {snapshot.disk_percent:.1f}% full", f"{snapshot.disk_free_gb:.1f} GB free"], ["large files", "temporary data", "applications"], ["review temporary data", "review large files"]))
    if baseline:
        med_ram = statistics.median(x.ram_percent for x in baseline)
        med_cpu = statistics.median(x.cpu_percent for x in baseline)
        if snapshot.ram_percent - med_ram >= 15:
            out.append(Diagnosis("RAM_ANOMALY", Risk.MEDIUM, "Memory usage is above device baseline", [f"Current {snapshot.ram_percent:.1f}% vs baseline median {med_ram:.1f}%"], ["unusual workload", "new background application"], ["inspect process history"]))
        if snapshot.cpu_percent - med_cpu >= 25:
            out.append(Diagnosis("CPU_ANOMALY", Risk.MEDIUM, "CPU usage is above device baseline", [f"Current {snapshot.cpu_percent:.1f}% vs baseline median {med_cpu:.1f}%"], ["unusual workload", "background process"], ["inspect process history"]))
    return out
