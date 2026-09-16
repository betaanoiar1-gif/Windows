from __future__ import annotations

import ctypes
from dataclasses import dataclass, asdict
from typing import Any, Callable

from .network import diagnose, recommended_repairs, repair, snapshot


@dataclass(frozen=True)
class RecoveryStep:
    action: str
    reason: str
    risk: str
    requires_reboot: bool = False
    requires_admin: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RISK = {
    "flush_dns": "safe",
    "renew_dhcp": "low",
    "reset_winsock": "medium",
    "reset_tcpip": "medium",
}

ADMIN_REQUIRED = {"renew_dhcp", "reset_winsock", "reset_tcpip"}


def is_admin() -> bool:
    """Return whether the current process has Windows administrator elevation."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def build_plan(issues: list[dict[str, Any]]) -> list[RecoveryStep]:
    steps: list[RecoveryStep] = []
    for action in recommended_repairs(issues):
        risk = RISK.get(action)
        if risk is None:
            continue
        reasons = [i.get("title", "") for i in issues if action in i.get("safe_actions", [])]
        steps.append(RecoveryStep(
            action=action,
            reason="; ".join(dict.fromkeys(x for x in reasons if x)),
            risk=risk,
            requires_reboot=action in {"reset_winsock", "reset_tcpip"},
            requires_admin=action in ADMIN_REQUIRED,
        ))
    return steps


def execute_verified(
    steps: list[RecoveryStep],
    confirm: Callable[[RecoveryStep], bool] | None = None,
    admin_check: Callable[[], bool] | None = None,
) -> list[dict[str, Any]]:
    """Execute only explicitly authorized, appropriately elevated recovery steps."""
    check_admin = admin_check or is_admin
    results: list[dict[str, Any]] = []
    for step in steps:
        if step.risk in {"medium", "high", "critical"} and confirm is None:
            results.append({"action": step.action, "skipped": True, "reason": "explicit confirmation required for elevated-risk repair"})
            continue
        if step.requires_admin and not check_admin():
            results.append({"action": step.action, "skipped": True, "reason": "administrator elevation required"})
            continue
        if confirm is not None and not confirm(step):
            results.append({"action": step.action, "skipped": True, "reason": "not confirmed"})
            continue
        try:
            result = repair(step.action)
        except (OSError, RuntimeError, ValueError) as exc:
            result = {"action": step.action, "ok": False, "skipped": False, "error": type(exc).__name__, "message": str(exc)}
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
    """Re-probe after recovery and report issue disappearance plus layered evidence."""
    after = snapshot(probes=probes)
    before_issues = diagnose(_snapshot_from_dict(before)) if isinstance(before, dict) else []
    after_issues = diagnose(after)
    before_codes = {x.get("code") for x in before_issues}
    after_codes = {x.get("code") for x in after_issues}
    before_gateway = ((before.get("internet") or {}).get("gateway_ping") or {})
    after_gateway = ((after.internet or {}).get("gateway_ping") or {})
    before_dns = ((before.get("internet") or {}).get("dns") or {})
    after_dns = ((after.internet or {}).get("dns") or {})
    before_loss = before_gateway.get("packet_loss_percent")
    after_loss = after_gateway.get("packet_loss_percent")
    return {
        "after": after.to_dict(),
        "resolved_issue_codes": sorted(str(x) for x in before_codes - after_codes if x),
        "remaining_issue_codes": sorted(str(x) for x in after_codes if x),
        "gateway_changed_to_ok": before_gateway.get("ok") is not True and after_gateway.get("ok") is True,
        "dns_changed_to_ok": before_dns.get("ok") is not True and after_dns.get("ok") is True,
        "packet_loss_improved": before_loss is not None and after_loss is not None and after_loss < before_loss,
        "issues_after": after_issues,
    }


def _snapshot_from_dict(value: dict[str, Any]):
    """Rehydrate the minimal NetworkSnapshot shape needed by diagnose()."""
    from .network import NetworkSnapshot
    return NetworkSnapshot(
        timestamp=float(value.get("timestamp", 0.0)),
        interfaces=value.get("interfaces", []),
        default_gateways=value.get("default_gateways", []),
        dns_servers=value.get("dns_servers", []),
        proxy=value.get("proxy", {}),
        internet=value.get("internet", {}),
        counters=value.get("counters", {}),
    )
