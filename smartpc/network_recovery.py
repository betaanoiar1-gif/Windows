from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable

from .network import diagnose, recommended_repairs, repair, snapshot


@dataclass(frozen=True)
class RecoveryStep:
    action: str
    reason: str
    risk: str
    requires_reboot: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RISK = {"flush_dns": "safe", "renew_dhcp": "low", "reset_winsock": "medium", "reset_tcpip": "medium"}


def build_plan(issues: list[dict[str, Any]]) -> list[RecoveryStep]:
    steps: list[RecoveryStep] = []
    for action in recommended_repairs(issues):
        reasons = [i.get("title", "") for i in issues if action in i.get("safe_actions", [])]
        if action == "flush_dns": reasons.append("DNS resolution failed")
        elif action == "renew_dhcp": reasons.append("Address or gateway configuration may be stale")
        elif action == "reset_winsock": reasons.append("Only consider after lower-impact recovery fails")
        elif action == "reset_tcpip": reasons.append("Only consider after lower-impact recovery fails")
        steps.append(RecoveryStep(action, "; ".join(dict.fromkeys(x for x in reasons if x)), RISK[action], action in {"reset_winsock", "reset_tcpip"}))
    return steps


def execute_verified(steps: list[RecoveryStep], confirm: Callable[[RecoveryStep], bool] | None = None) -> list[dict[str, Any]]:
    """Execute only explicitly authorized recovery steps and verify each step externally."""
    results = []
    for step in steps:
        if step.risk in {"medium", "high", "critical"} and confirm is None:
            results.append({"action": step.action, "skipped": True, "reason": "explicit confirmation required for elevated-risk repair"})
            continue
        if confirm is not None and not confirm(step):
            results.append({"action": step.action, "skipped": True, "reason": "not confirmed"})
            continue
        result = repair(step.action)
        results.append(result)
        if not result.get("ok"):
            break
    return results


def diagnose_and_plan(probes: bool = True) -> dict[str, Any]:
    current = snapshot(probes=probes)
    issues = diagnose(current)
    plan = build_plan(issues)
    return {"snapshot": current.to_dict(), "issues": issues, "plan": [x.to_dict() for x in plan]}


def verify_recovery(before: dict[str, Any], probes: bool = True) -> dict[str, Any]:
    after = snapshot(probes=probes)
    before_gateway = ((before.get("internet") or {}).get("gateway_ping") or {})
    after_gateway = ((after.internet or {}).get("gateway_ping") or {})
    before_dns = ((before.get("internet") or {}).get("dns") or {})
    after_dns = ((after.internet or {}).get("dns") or {})
    before_loss = before_gateway.get("packet_loss_percent")
    after_loss = after_gateway.get("packet_loss_percent")
    improved_loss = before_loss is not None and after_loss is not None and after_loss < before_loss
    return {
        "after": after.to_dict(),
        "gateway_changed_to_ok": before_gateway.get("ok") is not True and after_gateway.get("ok") is True,
        "dns_changed_to_ok": before_dns.get("ok") is not True and after_dns.get("ok") is True,
        "packet_loss_improved": improved_loss,
        "issues_after": diagnose(after),
    }
