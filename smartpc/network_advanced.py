from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Callable


CommandRunner = Callable[[list[str], int], tuple[int, str, str]]


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
    """Bounded HTTPS GET. HTTP errors still prove that TLS/HTTP transport reached the host."""
    started = time.perf_counter()
    try:
        timeout = max(0.5, min(15.0, float(timeout)))
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "SMARTPC-AI/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            status = int(getattr(response, "status", response.getcode()))
            return ProbeResult(url, 200 <= status < 500, round((time.perf_counter() - started) * 1000, 2), status)
    except urllib.error.HTTPError as exc:
        return ProbeResult(url, True, round((time.perf_counter() - started) * 1000, 2), exc.code)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        return ProbeResult(url, False, round((time.perf_counter() - started) * 1000, 2), error=str(exc))


def multi_https_probe(urls: tuple[str, ...] = (
    "https://www.microsoft.com/",
    "https://www.cloudflare.com/",
    "https://www.google.com/generate_204",
)) -> list[ProbeResult]:
    return [https_probe(url) for url in urls]


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = re.sub(r"\s+", " ", key.strip().lower())
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _first_value(fields: dict[str, str], *names: str) -> str | None:
    for name in names:
        if fields.get(name.lower()):
            return fields[name.lower()]
    return None


def _number(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_wifi_interfaces(text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", text.strip()) if text.strip() else []
    results: list[dict[str, Any]] = []
    for block in blocks:
        fields = _parse_key_values(block)
        if not fields:
            continue
        state = _first_value(fields, "state", "état")
        ssid = _first_value(fields, "ssid")
        signal = _number(_first_value(fields, "signal", "signal du réseau"))
        channel = _number(_first_value(fields, "channel", "canal"))
        radio = _first_value(fields, "radio type", "type de radio")
        rx = _number(_first_value(fields, "receive rate (mbps)", "vitesse de réception (mbits/s)"))
        tx = _number(_first_value(fields, "transmit rate (mbps)", "vitesse de transmission (mbits/s)"))
        if any(x is not None for x in (ssid, signal, channel, radio, rx, tx)) or state:
            results.append({"state": state, "ssid": ssid, "signal_percent": signal, "channel": int(channel) if channel is not None else None, "radio_type": radio, "receive_rate_mbps": rx, "transmit_rate_mbps": tx})
    return results


def wifi_diagnostics(runner: CommandRunner | None = None) -> dict[str, Any]:
    run = runner or _run
    state_rc, state_out, state_err = run(["netsh", "wlan", "show", "interfaces"], 10)
    driver_rc, driver_out, driver_err = run(["netsh", "wlan", "show", "drivers"], 10)
    return {"available": state_rc == 0, "interfaces": parse_wifi_interfaces(state_out), "interfaces_raw": state_out[-6000:], "drivers_raw": driver_out[-8000:], "command_errors": [x for x in (state_err, driver_err) if x], "driver_query_ok": driver_rc == 0}


def dns_latency(host: str, timeout: float = 3.0) -> ProbeResult:
    started = time.perf_counter()
    try:
        timeout = max(0.5, min(10.0, float(timeout)))
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            ok = bool(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        finally:
            socket.setdefaulttimeout(old)
        return ProbeResult(host, ok, round((time.perf_counter() - started) * 1000, 2))
    except (OSError, ValueError, TypeError) as exc:
        return ProbeResult(host, False, round((time.perf_counter() - started) * 1000, 2), error=str(exc))


def compare_dns_hosts(hosts: tuple[str, ...] = ("www.microsoft.com", "www.cloudflare.com", "www.google.com")) -> list[ProbeResult]:
    return [dns_latency(host) for host in hosts]


def _ping_payload(host: str, size: int, runner: CommandRunner | None = None) -> bool:
    run = runner or _run
    rc, _, _ = run(["ping", "-n", "1", "-f", "-l", str(size), "-w", "1500", host], 5)
    return rc == 0


def mtu_probe(host: str, payload_sizes: tuple[int, ...] | None = None, runner: CommandRunner | None = None) -> dict[str, Any]:
    """Read-only IPv4 DF probe. Estimates the largest successful payload; never changes MTU."""
    if payload_sizes is not None:
        sizes = tuple(sorted({max(576, min(1472, int(x))) for x in payload_sizes}, reverse=True))
        results = [{"payload_bytes": size, "ok": _ping_payload(host, size, runner)} for size in sizes]
        largest = max((x["payload_bytes"] for x in results if x["ok"]), default=None)
        return {"host": host, "samples": results, "largest_successful_payload": largest, "mtu_estimate": largest + 28 if largest is not None else None, "method": "sampled_df_ping"}

    low, high = 576, 1472
    samples: list[dict[str, Any]] = []
    while low <= high and len(samples) < 12:
        mid = (low + high) // 2
        ok = _ping_payload(host, mid, runner)
        samples.append({"payload_bytes": mid, "ok": ok})
        if ok:
            low = mid + 1
        else:
            high = mid - 1
    largest = max((x["payload_bytes"] for x in samples if x["ok"]), default=None)
    return {"host": host, "samples": samples, "largest_successful_payload": largest, "mtu_estimate": largest + 28 if largest is not None else None, "method": "binary_search_df_ping", "recommendation": "diagnostic evidence only; do not change MTU automatically"}


def summarize_https(results: list[ProbeResult]) -> dict[str, Any]:
    successful = [r for r in results if r.ok]
    return {"targets": len(results), "successful": len(successful), "failed": len(results) - len(successful), "reachable": bool(successful), "consistent_failure": bool(results) and not successful, "latencies_ms": [r.latency_ms for r in successful if r.latency_ms is not None]}


def advanced_snapshot(default_gateway: str | None = None, probes: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {"https": [], "https_summary": summarize_https([]), "dns": [], "wifi": wifi_diagnostics(), "mtu": None}
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
