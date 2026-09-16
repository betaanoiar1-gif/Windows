from __future__ import annotations

from collections import Counter
from typing import Any

import psutil


def connection_inventory(max_rows: int = 500) -> dict[str, Any]:
    """Read-only process/network correlation using OS-visible inet sockets."""
    limit = max(1, min(2000, int(max_rows)))
    rows: list[dict[str, Any]] = []
    by_process: Counter[str] = Counter()
    states: Counter[str] = Counter()
    errors = 0
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.Error, OSError) as exc:
        return {"available": False, "connections": [], "top_processes": [], "states": {}, "error": type(exc).__name__}
    for conn in connections[:limit]:
        pid = conn.pid
        name = None
        if pid:
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                errors += 1
        state = str(getattr(conn, "status", ""))
        states[state] += 1
        key = f"{name or 'unknown'}:{pid or '-'}"
        by_process[key] += 1
        rows.append({
            "pid": pid,
            "process": name,
            "family": str(getattr(conn, "family", "")),
            "type": str(getattr(conn, "type", "")),
            "status": state,
            "local": list(conn.laddr) if conn.laddr else None,
            "remote": list(conn.raddr) if conn.raddr else None,
        })
    return {
        "available": True,
        "connections": rows,
        "connection_count": len(rows),
        "top_processes": [{"process": key, "connections": count} for key, count in by_process.most_common(20)],
        "states": dict(states),
        "permission_errors": errors,
        "truncated": len(connections) > limit,
    }
