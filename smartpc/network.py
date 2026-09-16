from __future__ import annotations

import ipaddress
import os
import re
import socket
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import Any

import psutil


@dataclass
class NetworkSnapshot:
    timestamp: float
    interfaces: list[dict[str, Any]]
    default_gateways: list[str]
    dns_servers: list[str]
    proxy: dict[str, Any]
    internet: dict[str, Any]
    counters: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run(args: list[str], timeout: int = 15) -> tuple[int, str, str]:
    if os.name != "nt":
        return 1, "", "Windows-only network command"
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, shell=False)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def _windows_gateways() -> list[str]:
    rc, out, _ = _run(["ipconfig", "/all"])
    if rc != 0:
        return []
    gateways: list[str] = []
    for line in out.splitlines():
        if "Default Gateway" in line or "Passerelle par défaut" in line:
            value = line.split(":", 1)[-1].strip()
            if _valid_ip(value):
                gateways.append(value)
    return sorted(set(gateways))


def _windows_dns() -> list[str]:
    rc, out, _ = _run(["ipconfig", "/all"])
    if rc != 0:
        return []
    servers: list[str] = []
    collecting = False
    for line in out.splitlines():
        if "DNS Servers" in line or "Serveurs DNS" in line:
            collecting = True
            value = line.split(":", 1)[-1].strip()
            if _valid_ip(value):
                servers.append(value)
            continue
        if collecting:
            stripped = line.strip()
            if stripped and _valid_ip(stripped):
                servers.append(stripped)
            else:
                collecting = False
    return sorted(set(servers))


def _proxy() -> dict[str, Any]:
    if os.name != "nt":
        return {"enabled": False, "source": "unsupported"}
    rc, out, _ = _run(["netsh", "winhttp", "show", "proxy"])
    text = (out or "").strip()
    direct = "direct access" in text.lower() or "accès direct" in text.lower()
    return {"enabled": not direct, "raw": text, "source": "winhttp"}


def _interfaces() -> list[dict[str, Any]]:
    rows = []
    for name, addrs in psutil.net_if_addrs().items():
        ips = []
        for addr in addrs:
            if addr.family in (socket.AF_INET, socket.AF_INET6):
                ips.append({"address": addr.address, "netmask": addr.netmask})
        stats = psutil.net_if_stats().get(name)
        rows.append({
            "name": name,
            "addresses": ips,
            "is_up": bool(stats.isup) if stats else False,
            "speed_mbps": getattr(stats, "speed", 0) if stats else 0,
            "mtu": getattr(stats, "mtu", 0) if stats else 0,
        })
    return rows


def _probe_host(host: str, timeout: float = 2.0) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return {"host": host, "ok": True, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except OSError as exc:
        return {"host": host, "ok": False, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "error": str(exc)}


def _ping(host: str, count: int = 3) -> dict[str, Any]:
    if os.name != "nt":
        return {"host": host, "ok": False, "error": "Windows-only ping probe"}
    rc, out, err = _run(["ping", "-n", str(max(1, min(count, 5))), "-w", "1500", host], timeout=12)
    text = out + "\n" + err
    loss = None
    latency = None
    m = re.search(r"(\d+(?:\.\d+)?)%", text)
    if m:
        loss = float(m.group(1))
    m = re.search(r"(?:Average|Moyenne)[^=]*=\s*(\d+)\s*ms", text, re.I)
    if m:
        latency = float(m.group(1))
    return {"host": host, "ok": rc == 0, "packet_loss_percent": loss, "avg_latency_ms": latency}


def snapshot(probes: bool = True) -> NetworkSnapshot:
    counters = psutil.net_io_counters()
    internet = {
        "dns": _probe_host("www.microsoft.com") if probes else None,
        "https_dns": _probe_host("www.cloudflare.com") if probes else None,
        "gateway_ping": None,
    }
    gateways = _windows_gateways()
    if probes and gateways:
        internet["gateway_ping"] = _ping(gateways[0])
    return NetworkSnapshot(
        timestamp=time.time(),
        interfaces=_interfaces(),
        default_gateways=gateways,
        dns_servers=_windows_dns(),
        proxy=_proxy(),
        internet=internet,
        counters={"bytes_sent": counters.bytes_sent, "bytes_recv": counters.bytes_recv, "packets_sent": counters.packets_sent, "packets_recv": counters.packets_recv},
    )


def diagnose(s: NetworkSnapshot) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    up = [i for i in s.interfaces if i["is_up"] and i["addresses"]]
    if not up:
        issues.append({"code": "NET_NO_ACTIVE_INTERFACE", "severity": "high", "title": "No active network interface", "evidence": ["No up interface with an IP address was detected"]})
        return issues
    if not s.default_gateways:
        issues.append({"code": "NET_NO_GATEWAY", "severity": "high", "title": "No default gateway detected", "evidence": ["Windows did not report a default gateway"]})
    gp = (s.internet or {}).get("gateway_ping") or {}
    dns = (s.internet or {}).get("dns") or {}
    if s.default_gateways and gp.get("ok") is False:
        issues.append({"code": "NET_GATEWAY_UNREACHABLE", "severity": "high", "title": "Default gateway is not responding", "evidence": [str(gp)]})
    if dns.get("ok") is False:
        issues.append({"code": "NET_DNS_FAILURE", "severity": "medium", "title": "DNS resolution probe failed", "evidence": [str(dns)]})
    if s.proxy.get("enabled"):
        issues.append({"code": "NET_WINHTTP_PROXY", "severity": "medium", "title": "A WinHTTP proxy is configured", "evidence": ["A proxy can be intentional; verify it before changing it"], "safe_actions": ["review_proxy"]})
    return issues


def repair(action: str) -> dict[str, Any]:
    allowed = {
        "flush_dns": ["ipconfig", "/flushdns"],
        "renew_dhcp": ["ipconfig", "/renew"],
        "reset_winsock": ["netsh", "winsock", "reset"],
        "reset_tcpip": ["netsh", "int", "ip", "reset"],
        "release_renew": ["ipconfig", "/renew"],
    }
    if action not in allowed:
        raise ValueError(f"Unsupported network repair: {action}")
    rc, out, err = _run(allowed[action], timeout=60)
    return {"action": action, "returncode": rc, "ok": rc == 0, "stdout": out[-4000:], "stderr": err[-2000:], "requires_reboot": action in {"reset_winsock", "reset_tcpip"}}


def recommended_repairs(issues: list[dict[str, Any]]) -> list[str]:
    codes = {x.get("code") for x in issues}
    actions: list[str] = []
    if "NET_DNS_FAILURE" in codes:
        actions.append("flush_dns")
    if "NET_NO_GATEWAY" in codes:
        actions.append("renew_dhcp")
    if "NET_GATEWAY_UNREACHABLE" in codes:
        actions.extend(["renew_dhcp", "reset_winsock"])
    return list(dict.fromkeys(actions))
