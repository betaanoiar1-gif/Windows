from __future__ import annotations

import datetime as dt

from .ai import AIClient
from .config import Settings
from .db import DB
from .diagnostics import diagnose
from .health import health_score
from .learning import Baseline
from .monitor import snapshot
from .network import snapshot as network_snapshot, diagnose as diagnose_network, recommended_repairs
from .network_advanced import advanced_snapshot
from .network_diagnostics import dns_probe, https_probe, diagnose_connectivity
from .network_health import evaluate as evaluate_network_health
from .network_recovery import RISK, RecoveryStep, diagnose_and_plan, execute_verified
from .safety import authorize_all
from .storage import safe_quarantine, scan_temp


class Engine:
    def __init__(self, data_dir=None):
        self.settings = Settings.load(data_dir)
        self.data = self.settings.data_dir
        self.data.mkdir(parents=True, exist_ok=True)
        self.db = DB(self.data / "smartpc.db")
        self.ai = AIClient(timeout=self.settings.ai_timeout_seconds)

    def inspect(self, include_ai=True, network_probes=True):
        current = snapshot()
        self.db.snapshot(current)
        history = self.db.recent_snapshots(30)
        baseline = Baseline(history[:-1])
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=False)
        diagnoses = diagnose(current, history[:-1])
        net = network_snapshot(probes=network_probes)
        net_issues = diagnose_network(net)
        net_health = evaluate_network_health(net)
        connectivity = None
        advanced_network = None
        if network_probes:
            connectivity = diagnose_connectivity(dns_probe(), https_probe())
            gateway = net.default_gateways[0] if net.default_gateways else None
            advanced_network = advanced_snapshot(default_gateway=gateway, probes=True)
        payload = {
            "system": current.to_dict(),
            "health_score": health_score(current, diagnoses),
            "baseline": baseline.summary(),
            "diagnoses": [d.to_dict() for d in diagnoses],
            "network": net.to_dict(),
            "network_health": net_health.to_dict(),
            "network_connectivity": connectivity.to_dict() if connectivity else None,
            "network_advanced": advanced_network,
            "network_diagnoses": net_issues,
            "network_recommended_repairs": recommended_repairs(net_issues),
            "candidates": [{"candidate_id": str(i), **c.to_dict()} for i, c in enumerate(candidates)],
        }
        ai = self.ai.analyze(payload) if include_ai else {"mode": "disabled", "actions": []}
        return {
            "snapshot": current, "candidates": candidates, "diagnoses": diagnoses,
            "health_score": payload["health_score"], "baseline": payload["baseline"],
            "network": net, "network_health": net_health, "network_connectivity": connectivity,
            "network_advanced": advanced_network, "network_diagnoses": net_issues,
            "network_recommended_repairs": payload["network_recommended_repairs"], "ai": ai,
        }

    def optimize_safe(self):
        before = snapshot()
        self.db.snapshot(before)
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=True)
        moved = safe_quarantine(candidates, self.data / "quarantine", self.settings.max_quarantine_files)
        ts = dt.datetime.now(dt.timezone.utc).isoformat()
        for src, dst, token in moved:
            self.db.action(ts, "quarantine", src, f"ok:{dst}:{token}")
        after = snapshot()
        self.db.snapshot(after)
        return {"before": before, "after": after, "moved": moved}

    def network_inspect(self, probes=True):
        net = network_snapshot(probes=probes)
        issues = diagnose_network(net)
        health = evaluate_network_health(net)
        connectivity = None
        advanced_network = None
        if probes:
            connectivity = diagnose_connectivity(dns_probe(), https_probe())
            gateway = net.default_gateways[0] if net.default_gateways else None
            advanced_network = advanced_snapshot(default_gateway=gateway, probes=True)
        plan = diagnose_and_plan(probes=probes)
        return {
            "network": net, "health": health, "connectivity": connectivity,
            "advanced": advanced_network, "diagnoses": issues,
            "recommended_repairs": recommended_repairs(issues), "recovery_plan": plan["plan"],
        }

    def network_repair(self, action: str, confirm_medium=False, verify=True):
        risk = RISK.get(action)
        if risk is None:
            return {"before": None, "result": {"action": action, "ok": False, "skipped": True, "reason": "unsupported network repair"}, "after": None, "verification": None}
        before = self.network_inspect(probes=verify)
        step = RecoveryStep(
            action=action,
            reason="Explicit user-selected network repair",
            risk=risk,
            requires_reboot=action in {"reset_winsock", "reset_tcpip"},
            requires_admin=action in {"renew_dhcp", "reset_winsock", "reset_tcpip"},
        )
        confirm = (lambda _step: True) if (risk not in {"medium", "high", "critical"} or confirm_medium) else None
        results = execute_verified([step], confirm=confirm)
        result = results[0] if results else {"action": action, "ok": False, "skipped": True, "reason": "no recovery result"}
        after = self.network_inspect(probes=True) if verify and result.get("ok") else None
        verification = None
        if after is not None:
            before_score = before["health"].score
            after_score = after["health"].score
            verification = {
                "health_score_before": before_score,
                "health_score_after": after_score,
                "improved": after_score > before_score,
                "unchanged": after_score == before_score,
                "remaining_issues": after["diagnoses"],
                "advanced_after": after.get("advanced"),
            }
        self.db.action(
            dt.datetime.now(dt.timezone.utc).isoformat(), f"network:{action}", "network",
            "ok" if result.get("ok") else ("skipped:" + str(result.get("reason", "unknown"))),
        )
        return {"before": before, "result": result, "after": after, "verification": verification}

    def restore(self, token: str):
        from .storage import restore
        path = restore(self.data / "quarantine", token)
        self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), "restore", path, "ok")
        return path
