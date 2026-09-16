import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "SMARTPC AI"
MAINTENANCE_TASK_NAME = "SMARTPC AI Maintenance"


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


def maintenance_status():
    if not is_windows():
        return False
    return run_command(["schtasks", "/Query", "/TN", MAINTENANCE_TASK_NAME, "/FO", "LIST"]).returncode == 0


def install_startup_task():
    """Install observation at logon and bounded autonomous maintenance every 30 minutes."""
    if not is_windows():
        raise RuntimeError("Windows-only operation")
    exe = str(Path(sys.executable).resolve())
    script = str((Path(__file__).resolve().parents[1] / "main.py"))
    observation = run_command([
        "schtasks", "/Create", "/TN", TASK_NAME,
        "/TR", f'"{exe}" "{script}" --background --observe-only',
        "/SC", "ONLOGON", "/RL", "LIMITED", "/F",
    ])
    if observation.returncode != 0:
        raise RuntimeError(observation.stderr.strip() or observation.stdout.strip() or "Unable to create startup observation task")

    maintenance = run_command([
        "schtasks", "/Create", "/TN", MAINTENANCE_TASK_NAME,
        "/TR", f'"{exe}" "{script}" --background',
        "/SC", "MINUTE", "/MO", "30", "/RL", "LIMITED", "/F",
    ])
    if maintenance.returncode != 0:
        # Do not leave a half-installed startup configuration behind.
        run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        raise RuntimeError(maintenance.stderr.strip() or maintenance.stdout.strip() or "Unable to create maintenance task")
    return observation, maintenance


def remove_startup_task():
    if not is_windows():
        return None
    observation = run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    maintenance = run_command(["schtasks", "/Delete", "/TN", MAINTENANCE_TASK_NAME, "/F"])
    return observation, maintenance
