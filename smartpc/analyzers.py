import os
from pathlib import Path
from .models import Candidate, Action, Risk


def startup_candidates() -> list[Candidate]:
    out = []
    if os.name != "nt":
        return out
    try:
        import winreg
        keys = [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"), (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM")]
        for hive, subkey, label in keys:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, i)
                        out.append(Candidate(f"{label}:{name}", "startup", 0, 0, Risk.MEDIUM, Action.REVIEW, "Startup entry; read-only inventory", True, {"command": str(value), "hive": label}))
            except OSError:
                pass
    except ImportError:
        pass
    return out


def process_candidates(limit=25) -> list[Candidate]:
    try:
        import psutil
    except ImportError:
        return []
    rows = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            info = p.info
            rss = info.get("memory_info").rss if info.get("memory_info") else 0
            rows.append(Candidate(f"pid:{info['pid']}", "process", rss, 0, Risk.MEDIUM, Action.REVIEW, "Observed process; termination is never automatic", True, {"name": info.get("name") or "", "cpu": float(info.get("cpu_percent") or 0)}))
        except Exception:
            continue
    rows.sort(key=lambda x: x.size, reverse=True)
    return rows[:limit]
