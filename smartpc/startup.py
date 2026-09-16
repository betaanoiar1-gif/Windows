from __future__ import annotations

import os
from pathlib import Path


RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _read_run_key(winreg, root, path: str, label: str) -> list[dict]:
    rows = []
    try:
        with winreg.OpenKey(root, path) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _ = winreg.EnumValue(key, i)
                rows.append({"source": label, "name": name, "command": value})
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return rows


def entries() -> list[dict]:
    """Read startup entries without modifying the registry or startup folders."""
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []
    rows = [
        *_read_run_key(winreg, winreg.HKEY_CURRENT_USER, RUN_SUBKEY, "HKCU"),
        *_read_run_key(winreg, winreg.HKEY_LOCAL_MACHINE, RUN_SUBKEY, "HKLM"),
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        folder = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        try:
            if folder.is_dir():
                rows.extend({"source": "startup_folder", "name": p.name, "command": str(p)} for p in folder.iterdir())
        except OSError:
            pass
    return rows
