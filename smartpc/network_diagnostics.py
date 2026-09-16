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
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return {
            "ok": bool(addresses),
            "host": host,
            "addresses": sorted({x[4][0] for x in addresses}),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except OSError as exc:
        return {"ok": False, "host": host, "addresses": [], "latency_ms": round((time.perf_counter() - started) * 1000, 2), "error": str(exc)}


def https_probe(url: str = "https://www.microsoft.com/", timeout: float = 5.0) -> dict[str, Any]:
    started = time.perf_counter()
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SMARTPC-AI/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"ok": 200 <= response.status < 500, "status": response.status, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url}
    except urllib.error.HTTPError as exc:
        return {"ok": True, "status": exc.code, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "status": None, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "url": url, "error": str(exc)}


def diagnose_connectivity(dns: dict[str, Any], https: dict[str, Any]) -> ConnectivityDiagnosis:
    dns_ok = bool(dns.get("ok"))
    https_ok = bool(https.get("ok"))
    if https_ok:
        state = "internet_reachable"
    elif dns_ok:
        state = "dns_only"
    elif dns.get("error") and https.get("error"):
        state = "unreachable"
    else:
        state = "partially_reachable"
    latency = https.get("latency_ms") if https_ok else dns.get("latency_ms")
    evidence = [f"DNS: {'ok' if dns_ok else 'failed'}", f"HTTPS: {'ok' if https_ok else 'failed'}"]
    if dns.get("error"):
        evidence.append(f"DNS error: {str(dns['error'])[:300]}")
    if https.get("error"):
        evidence.append(f"HTTPS error: {str(https['error'])[:300]}")
    return ConnectivityDiagnosis(state, dns_ok, https_ok, latency, evidence)
