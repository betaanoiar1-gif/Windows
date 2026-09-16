import os, subprocess, sys
from pathlib import Path

def is_windows(): return os.name == "nt"

def run_command(args, timeout=20):
    if not is_windows(): raise RuntimeError("Windows-only operation")
    return subprocess.run(args,capture_output=True,text=True,timeout=timeout,shell=False)

def startup_status():
    r=run_command(["schtasks","/Query","/TN","SMARTPC AI","/FO","LIST"])
    return r.returncode==0

def install_startup_task():
    """Creates a user logon task. Explicit installer action only; never run automatically."""
    if not is_windows(): raise RuntimeError("Windows-only operation")
    exe=sys.executable; script=str(Path(__file__).resolve().parents[1]/"main.py")
    return run_command(["schtasks","/Create","/TN","SMARTPC AI","/TR",f'"{exe}" "{script}" --background',"/SC","ONLOGON","/RL","LIMITED","/F"])

def remove_startup_task():
    return run_command(["schtasks","/Delete","/TN","SMARTPC AI","/F"])
