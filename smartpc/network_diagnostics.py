from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ConnectivityDiagnosis:
    state: str
    dns_ok: bool | None
    https_ok: bool | None
    latency_ms: float | None
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dns_probe(host: str = "www.microsoft.com", timeout: float = 3.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        timeout = max(0.5, min(10.0, float(timeout)))
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        finally:
            socket.setdefaulttimeout(old)
        return {
            "ok": bool(addresses),
            "host": host,
            "addresses": sorted({x[4][0] for x in addresses}),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "host": host, "addresses": [], "latency_ms": round((time.perf_counter() - started) * 1000, 2), "error": str(exc)}


def https_probe(url: str = "https://www.microsoft.com/", timeout: float = 5.0) -> dict[str, Any]:
    """Use a bounded GET so a successful transport is not dependent on HEAD support."""
    started = time.perf_counter()
    try:
        timeout = max(0.5, min(15.0, float(timeout)))
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "SMARTPC-AI/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            status = int(getattr(response, "status", response.getcode()))
            return {"ok": 200 <= status < 500, "status": status, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url}
    except urllib.error.HTTPError as exc:
        return {"ok": True, "status": exc.code, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        return {"ok": False, "status": None, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url, "error": str(exc)}


def diagnose_connectivity(dns: dict[str, Any], https: dict[str, Any]) -> ConnectivityDiagnosis:
    dns_ok = True if dns.get("ok") is True else False if dns.get("ok") is False else None
    https_ok = True if https.get("ok") is True else False if https.get("ok") is False else None
    if https_ok is True:
        state = "internet_reachable"
    elif dns_ok is True and https_ok is False:
        state = "dns_only"
    elif dns_ok is False and https_ok is False:
        state = "unreachable"
    else:
        state = "partially_reachable"
    latency = https.get("latency_ms") if https_ok else dns.get("latency_ms")
    evidence = [f"DNS: {'ok' if dns_ok else 'failed' if dns_ok is False else 'unknown'}", f"HTTPS: {'ok' if https_ok else 'failed' if https_ok is False else 'unknown'}"]
    if dns.get("error"):
        evidence.append(f"DNS error: {str(dns['error'])[:300]}")
    if https.get("error"):
        evidence.append(f"HTTPS error: {str(https['error'])[:300]}")
    return ConnectivityDiagnosis(state, dns_ok, https_ok, latency, evidence)
