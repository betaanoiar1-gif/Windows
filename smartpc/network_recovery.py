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
        if action == "flush_dns": reasons.append("DNS probe failed")
        elif action == "renew_dhcp": reasons.append("Gateway/address configuration may be stale")
        elif action == "reset_winsock": reasons.append("Basic recovery may not have restored gateway connectivity")
        steps.append(RecoveryStep(action, "; ".join(dict.fromkeys(x for x in reasons if x)), RISK[action], action in {"reset_winsock", "reset_tcpip"}))
    return steps


def execute_verified(steps: list[RecoveryStep], confirm: Callable[[RecoveryStep], bool] | None = None) -> list[dict[str, Any]]:
    results = []
    for step in steps:
        if confirm and not confirm(step):
            results.append({"action": step.action, "skipped": True})
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
    return {
        "after": after.to_dict(),
        "gateway_changed_to_ok": before_gateway.get("ok") is not True and after_gateway.get("ok") is True,
        "dns_changed_to_ok": before_dns.get("ok") is not True and after_dns.get("ok") is True,
        "issues_after": diagnose(after),
    }
