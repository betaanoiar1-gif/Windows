import datetime as dt
from .ai import AIClient
from .config import Settings
from .db import DB
from .diagnostics import diagnose
from .health import health_score
from .learning import Baseline
from .monitor import snapshot
from .network import snapshot as network_snapshot, diagnose as diagnose_network, recommended_repairs, repair as repair_network
from .network_diagnostics import dns_probe, https_probe, diagnose_connectivity
from .network_health import evaluate as evaluate_network_health
from .network_recovery import diagnose_and_plan, verify_recovery
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
        if network_probes:
            dprobe = dns_probe()
            hprobe = https_probe()
            connectivity = diagnose_connectivity(dprobe, hprobe)
        payload = {
            "system": current.to_dict(),
            "health_score": health_score(current, diagnoses),
            "baseline": baseline.summary(),
            "diagnoses": [d.to_dict() for d in diagnoses],
            "network": net.to_dict(),
            "network_health": net_health.to_dict(),
            "network_connectivity": connectivity.to_dict() if connectivity else None,
            "network_diagnoses": net_issues,
            "network_recommended_repairs": recommended_repairs(net_issues),
            "candidates": [{"candidate_id": str(i), **c.to_dict()} for i, c in enumerate(candidates)]
        }
        ai = self.ai.analyze(payload) if include_ai else {"mode": "disabled", "actions": []}
        return {"snapshot": current, "candidates": candidates, "diagnoses": diagnoses, "health_score": payload["health_score"], "baseline": payload["baseline"], "network": net, "network_health": net_health, "network_connectivity": connectivity, "network_diagnoses": net_issues, "network_recommended_repairs": payload["network_recommended_repairs"], "ai": ai}

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
        if probes:
            connectivity = diagnose_connectivity(dns_probe(), https_probe())
        plan = diagnose_and_plan(probes=probes)
        return {"network": net, "health": health, "connectivity": connectivity, "diagnoses": issues, "recommended_repairs": recommended_repairs(issues), "recovery_plan": plan["plan"]}

    def network_repair(self, action: str, confirm_medium=False, verify=True):
        before = self.network_inspect(probes=True)
        from .network_recovery import RISK
        if RISK.get(action) in {"medium", "high", "critical"} and not confirm_medium:
            return {"before": before, "result": {"action": action, "ok": False, "skipped": True, "reason": "explicit confirmation required"}, "after": None}
        result = repair_network(action)
        after = self.network_inspect(probes=True) if verify else None
        verification = None
        if after is not None:
            before_score = before["health"].score
            after_score = after["health"].score
            verification = {"health_score_before": before_score, "health_score_after": after_score, "improved": after_score > before_score, "remaining_issues": after["diagnoses"]}
        self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), f"network:{action}", "network", "ok" if result["ok"] else "failed")
        return {"before": before, "result": result, "after": after, "verification": verification}

    def restore(self, token: str):
        from .storage import restore
        path = restore(self.data / "quarantine", token)
        self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), "restore", path, "ok")
        return path
