from __future__ import annotations

import statistics
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class NetworkHealth:
    score: float
    state: str
    packet_loss_percent: float | None
    gateway_latency_ms: float | None
    dns_latency_ms: float | None
    active_interfaces: int
    bytes_per_second: float
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _value(probe: dict[str, Any] | None, key: str) -> float | None:
    if not probe:
        return None
    try:
        return float(probe[key]) if probe.get(key) is not None else None
    except (TypeError, ValueError):
        return None


def evaluate(current, previous=None, interval_seconds: float = 1.0, connectivity: Any = None) -> NetworkHealth:
    """Score health from layered evidence; gateway ICMP failure is not treated as outage when HTTPS works."""
    active = sum(1 for item in current.interfaces if item.get("is_up") and item.get("addresses"))
    gateway = (current.internet or {}).get("gateway_ping") or {}
    dns = (current.internet or {}).get("dns") or {}
    loss = _value(gateway, "packet_loss_percent")
    glat = _value(gateway, "avg_latency_ms")
    dlat = _value(dns, "latency_ms")
    https_ok = getattr(connectivity, "https_ok", None)
    score = 100.0
    evidence: list[str] = []
    if active == 0:
        score -= 80
        evidence.append("No active interface with an IP address")
    if not current.default_gateways:
        score -= 35
        evidence.append("No default gateway")
    gateway_icmp_failed = gateway.get("ok") is False
    if gateway_icmp_failed:
        if https_ok is True:
            evidence.append("Default gateway did not answer ICMP; external HTTPS connectivity is working")
        else:
            score -= 35
            evidence.append("Default gateway ICMP probe failed")
    if dns.get("ok") is False:
        score -= 25
        evidence.append("DNS probe failed")
    if loss is not None and not (gateway_icmp_failed and https_ok is True):
        score -= min(35, loss * 0.8)
        if loss > 5:
            evidence.append(f"Gateway packet loss {loss:.1f}%")
    if glat is not None and glat > 100:
        score -= min(15, (glat - 100) / 20)
        evidence.append(f"High gateway latency {glat:.1f} ms")
    if current.proxy.get("enabled"):
        evidence.append("WinHTTP proxy is configured; it may be intentional")
    if previous is not None:
        dt = max(0.1, interval_seconds)
        sent = max(0, current.counters.get("bytes_sent", 0) - previous.counters.get("bytes_sent", 0))
        recv = max(0, current.counters.get("bytes_recv", 0) - previous.counters.get("bytes_recv", 0))
        bps = (sent + recv) / dt
    else:
        bps = 0.0
    score = max(0.0, min(100.0, score))
    state = "healthy" if score >= 85 else "degraded" if score >= 60 else "poor"
    return NetworkHealth(score, state, loss, glat, dlat, active, bps, evidence)


def stability(samples: list[NetworkHealth]) -> dict[str, Any]:
    if not samples:
        return {"samples": 0, "score_avg": None, "score_stddev": None, "degraded_ratio": None}
    scores = [x.score for x in samples]
    degraded = sum(x.state != "healthy" for x in samples) / len(samples)
    return {"samples": len(samples), "score_avg": round(statistics.mean(scores), 2), "score_stddev": round(statistics.pstdev(scores), 2), "degraded_ratio": round(degraded, 3)}
