from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ProbeResult:
    target: str
    ok: bool
    latency_ms: float | None = None
    status: int | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(args: list[str], timeout: int = 10) -> tuple[int, str, str]:
    if os.name != "nt":
        return 1, "", "Windows-only diagnostic"
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)


def https_probe(url: str, timeout: float = 5.0) -> ProbeResult:
    """Bounded HTTPS GET. A HTTP error still proves that transport reached the host."""
    started = time.perf_counter()
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "SMARTPC-AI/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            return ProbeResult(url, True, round((time.perf_counter() - started) * 1000, 2), response.status)
    except urllib.error.HTTPError as exc:
        return ProbeResult(url, True, round((time.perf_counter() - started) * 1000, 2), exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return ProbeResult(url, False, round((time.perf_counter() - started) * 1000, 2), error=str(exc))


def multi_https_probe(urls: tuple[str, ...] = (
    "https://www.microsoft.com/",
    "https://www.cloudflare.com/",
    "https://www.google.com/generate_204",
)) -> list[ProbeResult]:
    return [https_probe(url) for url in urls]


def wifi_diagnostics() -> dict[str, Any]:
    """Read-only Wi-Fi state/driver information; no adapter changes are performed."""
    state_rc, state_out, state_err = _run(["netsh", "wlan", "show", "interfaces"])
    driver_rc, driver_out, driver_err = _run(["netsh", "wlan", "show", "drivers"])
    text = state_out + "\n" + state_err
    fields: dict[str, str] = {}
    patterns = {
        "state": r"(?:State|État)\s*:\s*(.+)",
        "ssid": r"(?:SSID)\s*:\s*(.+)",
        "signal": r"(?:Signal|Signal du réseau)\s*:\s*(\d+)%",
        "channel": r"(?:Channel|Canal)\s*:\s*(\d+)",
        "radio": r"(?:Radio type|Type de radio)\s*:\s*(.+)",
        "receive_rate_mbps": r"(?:Receive rate \(Mbps\)|Vitesse de réception \(Mbits/s\))\s*:\s*([\d.]+)",
        "transmit_rate_mbps": r"(?:Transmit rate \(Mbps\)|Vitesse de transmission \(Mbits/s\))\s*:\s*([\d.]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            fields[key] = match.group(1).strip()
    return {
        "available": state_rc == 0,
        "fields": fields,
        "interfaces_raw": state_out[-6000:],
        "drivers_raw": driver_out[-8000:],
        "command_errors": [x for x in (state_err, driver_err) if x],
        "driver_query_ok": driver_rc == 0,
    }


def dns_latency(host: str, timeout: float = 3.0) -> ProbeResult:
    started = time.perf_counter()
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        ok = bool(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        return ProbeResult(host, ok, round((time.perf_counter() - started) * 1000, 2))
    except OSError as exc:
        return ProbeResult(host, False, round((time.perf_counter() - started) * 1000, 2), error=str(exc))
    finally:
        socket.setdefaulttimeout(old)


def compare_dns_hosts(hosts: tuple[str, ...] = (
    "www.microsoft.com", "www.cloudflare.com", "www.google.com"
)) -> list[ProbeResult]:
    return [dns_latency(host) for host in hosts]


def mtu_probe(host: str, payload_sizes: tuple[int, ...] = (1472, 1400, 1300, 1200)) -> dict[str, Any]:
    """Read-only DF ping sampling. Results are evidence only; MTU is never changed automatically."""
    results: list[dict[str, Any]] = []
    for size in payload_sizes:
        rc, out, err = _run(["ping", "-n", "1", "-f", "-l", str(size), "-w", "2000", host], timeout=5)
        results.append({"payload_bytes": size, "ok": rc == 0, "output": (out or err)[-1500:]})
    return {"host": host, "samples": results, "recommendation": "investigate only if repeated failures show a path-MTU pattern"}


def summarize_https(results: list[ProbeResult]) -> dict[str, Any]:
    successful = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    return {
        "targets": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "reachable": bool(successful),
        "consistent_failure": bool(results) and not successful,
        "latencies_ms": [r.latency_ms for r in successful if r.latency_ms is not None],
    }


def advanced_snapshot(default_gateway: str | None = None, probes: bool = True) -> dict[str, Any]:
    """Collect advanced read-only evidence in one bounded call."""
    result: dict[str, Any] = {
        "https": [], "https_summary": summarize_https([]), "dns": [],
        "wifi": wifi_diagnostics(), "mtu": None,
    }
    if not probes:
        return result
    https_results = multi_https_probe()
    dns_results = compare_dns_hosts()
    result["https"] = [x.to_dict() for x in https_results]
    result["https_summary"] = summarize_https(https_results)
    result["dns"] = [x.to_dict() for x in dns_results]
    if default_gateway:
        result["mtu"] = mtu_probe(default_gateway)
    return result
