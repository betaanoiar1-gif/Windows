import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "SMARTPC AI"

def is_windows():
    return os.name == "nt"

def run_command(args, timeout=20):
    if not is_windows():
        raise RuntimeError("Windows-only operation")
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)

def startup_status():
    if not is_windows():
        return False
    return run_command(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]).returncode == 0

def install_startup_task():
    """Install a limited ONLOGON task only when explicitly requested."""
    if not is_windows():
        raise RuntimeError("Windows-only operation")
    exe = str(Path(sys.executable).resolve())
    script = str((Path(__file__).resolve().parents[1] / "main.py"))
    result = run_command(["schtasks", "/Create", "/TN", TASK_NAME, "/TR", f'"{exe}" "{script}" --background', "/SC", "ONLOGON", "/RL", "LIMITED", "/F"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Unable to create startup task")
    return result

def remove_startup_task():
    if not is_windows():
        return None
    return run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
