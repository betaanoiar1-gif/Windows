from __future__ import annotations

import os
import winreg
from pathlib import Path

RUN_KEYS = (
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
)


def _read_run_key(root, path: str) -> list[dict]:
    rows = []
    try:
        with winreg.OpenKey(root, path) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _ = winreg.EnumValue(key, i)
                rows.append({"source": path, "name": name, "command": value})
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return rows


def entries() -> list[dict]:
    """Read startup entries without modifying the registry or startup folders."""
    if os.name != "nt":
        return []
    rows = [item for root, path in RUN_KEYS for item in _read_run_key(root, path)]
    appdata = os.environ.get("APPDATA")
    if appdata:
        folder = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        if folder.is_dir():
            rows.extend({"source": "startup_folder", "name": p.name, "command": str(p)} for p in folder.iterdir())
    return rows
