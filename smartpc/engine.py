from __future__ import annotations

import datetime as dt
import time
import uuid
from pathlib import Path

from .ai import AIClient
from .config import Settings
from .db import DB
from .diagnostics import diagnose
from .disk_cleanup import scan_deep, summarize as summarize_disk_cleanup
from .health import health_score
from .learning import Baseline
from .monitor import snapshot
from .network import snapshot as network_snapshot, diagnose as diagnose_network, recommended_repairs
from .network_advanced import advanced_snapshot
from .network_diagnostics import dns_probe, https_probe, diagnose_connectivity
from .network_health import evaluate as evaluate_network_health
from .network_processes import connection_inventory
from .network_recovery import RISK, RecoveryStep, build_plan, execute_verified
from .policy import Policy, PolicyEngine
from .safety import authorize_all
from .storage import safe_quarantine, scan_temp, restore


class Engine:
    def __init__(self, data_dir=None):
        self.settings = Settings.load(data_dir)
        self.data = self.settings.data_dir
        self.data.mkdir(parents=True, exist_ok=True)
        self.db = DB(self.data / "smartpc.db")
        self.ai = AIClient(timeout=self.settings.ai_timeout_seconds)
        self.auto_policy = PolicyEngine(Policy(
            auto_safe_cleanup=self.settings.auto_safe_cleanup,
            max_auto_files=self.settings.auto_max_files,
            max_auto_bytes=self.settings.auto_max_bytes,
        ))

    def inspect(self, include_ai=True, network_probes=True):
        current = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
        self.db.snapshot(current)
        history = self.db.recent_snapshots(30)
        baseline = Baseline(history[:-1])
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=False)
        disk_candidates = scan_deep(max_files=self.settings.max_scan_files, min_age_days=1.0)
        disk_summary = summarize_disk_cleanup(disk_candidates)
        diagnoses = diagnose(current, history[:-1])
        net = network_snapshot(probes=network_probes)
        connectivity = None
        advanced_network = None
        if network_probes:
            connectivity = diagnose_connectivity(dns_probe(), https_probe())
            gateway = net.default_gateways[0] if net.default_gateways else None
            advanced_network = advanced_snapshot(default_gateway=gateway, probes=True)
        net_issues = diagnose_network(net, connectivity=connectivity)
        net_health = evaluate_network_health(net, connectivity=connectivity)
        payload = {
            "system": current.to_dict(), "health_score": health_score(current, diagnoses),
            "baseline": baseline.summary(), "diagnoses": [d.to_dict() for d in diagnoses],
            "disk_cleanup": disk_summary, "network": net.to_dict(),
            "network_health": net_health.to_dict(),
            "network_connectivity": connectivity.to_dict() if connectivity else None,
            "network_advanced": advanced_network,
            "network_diagnoses": net_issues,
            "network_recommended_repairs": recommended_repairs(net_issues),
            "network_processes": connection_inventory() if network_probes else None,
            "candidates": [{"candidate_id": str(i), **c.to_dict()} for i, c in enumerate(candidates)],
        }
        ai = self.ai.analyze(payload) if include_ai else {"mode": "disabled", "actions": []}
        return {
            "snapshot": current, "candidates": candidates, "diagnoses": diagnoses,
            "health_score": payload["health_score"], "baseline": payload["baseline"],
            "disk_cleanup": disk_summary, "network": net, "network_health": net_health,
            "network_connectivity": connectivity, "network_advanced": advanced_network,
            "network_processes": payload["network_processes"], "network_diagnoses": net_issues,
            "network_recommended_repairs": payload["network_recommended_repairs"], "ai": ai,
        }

    def deep_disk_scan(self):
        candidates = scan_deep(max_files=self.settings.max_scan_files, min_age_days=1.0)
        return {"candidates": candidates, "summary": summarize_disk_cleanup(candidates)}

    def _disk_pressure(self, current):
        free_gb = max(float(current.disk_free_gb), 0.0)
        free_percent = max(0.0, 100.0 - float(current.disk_percent))
        total_gb = (free_gb / (free_percent / 100.0)) if free_percent > 0 else 0.0
        critical = free_percent <= self.settings.auto_cleanup_free_percent or free_gb <= self.settings.auto_cleanup_free_gb
        return {
            "drive": "system", "total_gb": round(total_gb, 2), "free_gb": round(free_gb, 2),
            "free_percent": round(free_percent, 2), "state": "critical" if critical else "normal",
            "auto_cleanup_triggered": bool(critical and self.settings.auto_safe_cleanup),
        }

    @staticmethod
    def _parse_snapshot_time(value: str) -> float | None:
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError, OverflowError):
            return None

    def _predict_disk_pressure(self, history, current):
        points = []
        for item in history:
            ts = self._parse_snapshot_time(item.timestamp)
            if ts is not None and item.disk_free_gb >= 0:
                points.append((ts, float(item.disk_free_gb)))
        now = self._parse_snapshot_time(current.timestamp)
        if now is not None:
            points.append((now, float(max(current.disk_free_gb, 0.0))))
        points.sort(key=lambda x: x[0])
        filtered = []
        for point in points:
            if not filtered or point[0] - filtered[-1][0] >= 300:
                filtered.append(point)
            else:
                filtered[-1] = point
        points = filtered[-20:]
        result = {"enabled": bool(self.settings.auto_predictive_cleanup), "samples": len(points), "rate_gb_per_hour": 0.0, "projected_free_gb": None, "horizon_hours": self.settings.auto_predictive_horizon_hours, "triggered": False, "reason": "insufficient historical samples"}
        if not self.settings.auto_predictive_cleanup:
            result["reason"] = "predictive maintenance disabled"
            return result
        if len(points) < self.settings.auto_predictive_min_samples:
            return result
        rates = []
        for (t0, f0), (t1, f1) in zip(points, points[1:]):
            hours = (t1 - t0) / 3600.0
            if hours <= 0:
                continue
            consumed = f0 - f1
            if consumed > 0:
                rates.append(consumed / hours)
        if not rates:
            result["reason"] = "no measured C: consumption trend"
            return result
        rates.sort()
        rate = rates[len(rates) // 2]
        result["rate_gb_per_hour"] = round(rate, 4)
        if rate < self.settings.auto_predictive_min_rate_gb_hour:
            result["reason"] = "measured growth below predictive noise floor"
            return result
        current_free = max(float(current.disk_free_gb), 0.0)
        target_free = max(self.settings.auto_cleanup_free_gb, current_free * (self.settings.auto_cleanup_free_percent / 100.0))
        projected = max(0.0, current_free - rate * self.settings.auto_predictive_horizon_hours)
        result["projected_free_gb"] = round(projected, 2)
        if projected <= target_free and current_free > target_free:
            result["triggered"] = True
            result["reason"] = "measured consumption projects threshold breach within horizon"
        else:
            result["reason"] = "projected free space remains above cleanup threshold"
        return result

    def _automatic_gate(self):
        now = time.time()
        last = self.db.last_maintenance(successful_only=True)
        if last:
            elapsed_minutes = max(0.0, (now - float(last[0])) / 60.0)
            if elapsed_minutes < self.settings.auto_cooldown_minutes:
                return False, f"automatic cleanup cooldown active ({round(self.settings.auto_cooldown_minutes - elapsed_minutes, 1)} min remaining)"
        used = self.db.maintenance_bytes_since(now - 86400.0)
        if used >= self.settings.auto_daily_max_bytes:
            return False, "automatic daily cleanup budget exhausted"
        return True, None

    @staticmethod
    def _moved_bytes(moved) -> int:
        total = 0
        for _src, dst, _token in moved:
            try:
                total += max(0, Path(dst).stat().st_size)
            except OSError:
                continue
        return total

    def autonomous_maintenance(self):
        """Fast unattended cycle with the complete system snapshot and full functionality."""
        # Keep the complete telemetry used by diagnosis/baseline/history. The only
        # speed optimization here is the short sampling interval configured in Settings.
        before = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
        history = self.db.recent_snapshots(30)
        self.db.snapshot(before)
        pressure = self._disk_pressure(before)
        prediction = self._predict_disk_pressure(history, before)
        trigger = bool(pressure["auto_cleanup_triggered"] or prediction["triggered"])
        moved = []
        skipped_reason = None
        started = time.time()
        owner = uuid.uuid4().hex
        acquired = self.db.try_acquire_maintenance(owner)
        if not acquired:
            skipped_reason = "another autonomous maintenance cycle is already running"
            self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), "autonomous_maintenance", "maintenance", "skipped:" + skipped_reason)
            return {"before": before, "after": before, "pressure_before": pressure, "prediction": prediction, "pressure_after": pressure, "triggered": trigger, "moved": [], "skipped_reason": skipped_reason, "mode": "autonomous_predictive_safe_maintenance"}
        try:
            if not self.settings.auto_safe_cleanup:
                skipped_reason = "automatic cleanup disabled"
            elif not trigger:
                skipped_reason = prediction["reason"]
            else:
                allowed, gate_reason = self._automatic_gate()
                if not allowed:
                    skipped_reason = gate_reason
                else:
                    candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=True)
                    eligible = []
                    count = 0
                    used_bytes = 0
                    for candidate in candidates:
                        if self.auto_policy.allow(candidate, count, used_bytes):
                            eligible.append(candidate)
                            count += 1
                            used_bytes += int(candidate.size)
                    moved = safe_quarantine(eligible, self.data / "quarantine", limit=self.settings.auto_max_files, max_bytes=self.settings.auto_max_bytes)
                    ts = dt.datetime.now(dt.timezone.utc).isoformat()
                    for src, dst, token in moved:
                        self.db.action(ts, "autonomous_quarantine", src, f"ok:{dst}:{token}")
            after = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
            if moved and after.disk_free_gb + 0.10 < before.disk_free_gb:
                restored = 0
                for _src, _dst, token in reversed(moved):
                    try:
                        restore(self.data / "quarantine", token)
                        restored += 1
                    except (OSError, KeyError, FileNotFoundError, FileExistsError):
                        continue
                moved = []
                after = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
                skipped_reason = f"verification rollback: free space decreased after cleanup; restored {restored} file(s)"
                result = "rolled_back"
            else:
                result = "ok" if moved else "no_change"
            self.db.snapshot(after)
            after_pressure = self._disk_pressure(after)
            bytes_moved = self._moved_bytes(moved)
            self.db.maintenance_run(started, time.time(), "disk_pressure" if pressure["auto_cleanup_triggered"] else "predictive_pressure", len(moved), bytes_moved, before.disk_free_gb, after.disk_free_gb, result, skipped_reason)
            return {"before": before, "after": after, "pressure_before": pressure, "prediction": prediction, "triggered": trigger, "pressure_after": after_pressure, "moved": moved, "skipped_reason": skipped_reason, "mode": "autonomous_predictive_safe_maintenance"}
        finally:
            self.db.release_maintenance(owner)

    def optimize_safe(self):
        before = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
        self.db.snapshot(before)
        candidates = authorize_all(scan_temp(self.settings.max_scan_files), auto=True)
        moved = safe_quarantine(candidates, self.data / "quarantine", self.settings.max_quarantine_files)
        ts = dt.datetime.now(dt.timezone.utc).isoformat()
        for src, dst, token in moved:
            self.db.action(ts, "quarantine", src, f"ok:{dst}:{token}")
        after = snapshot(self.settings.fast_monitor_interval, self.settings.max_process_rows)
        self.db.snapshot(after)
        return {"before": before, "after": after, "moved": moved}

    def network_inspect(self, probes=True):
        net = network_snapshot(probes=probes)
        connectivity = None
        advanced_network = None
        process_network = connection_inventory() if probes else None
        if probes:
            connectivity = diagnose_connectivity(dns_probe(), https_probe())
            gateway = net.default_gateways[0] if net.default_gateways else None
            advanced_network = advanced_snapshot(default_gateway=gateway, probes=True)
        issues = diagnose_network(net, connectivity=connectivity)
        health = evaluate_network_health(net, connectivity=connectivity)
        plan = [step.to_dict() for step in build_plan(issues)]
        return {"network": net, "health": health, "connectivity": connectivity, "advanced": advanced_network, "process_network": process_network, "diagnoses": issues, "recommended_repairs": recommended_repairs(issues), "recovery_plan": plan}

    def network_repair(self, action: str, confirm_medium=False, verify=True):
        risk = RISK.get(action)
        if risk is None:
            return {"before": None, "result": {"action": action, "ok": False, "skipped": True, "reason": "unsupported network repair"}, "after": None, "verification": None}
        before = self.network_inspect(probes=verify)
        step = RecoveryStep(action=action, reason="Explicit user-selected network repair", risk=risk, requires_reboot=action in {"reset_winsock", "reset_tcpip"}, requires_admin=action in {"renew_dhcp", "reset_winsock", "reset_tcpip"})
        confirm = (lambda _step: True) if risk == "safe" else ((lambda _step: True) if (risk == "low" and confirm_medium) else None)
        results = execute_verified([step], confirm=confirm)
        result = results[0] if results else {"action": action, "ok": False, "skipped": True, "reason": "no recovery result"}
        after = self.network_inspect(probes=True) if verify and result.get("ok") else None
        verification = None
        if after is not None:
            before_score = before["health"].score
            after_score = after["health"].score
            before_codes = {x.get("code") for x in before["diagnoses"] if isinstance(x, dict) and x.get("code")}
            after_codes = {x.get("code") for x in after["diagnoses"] if isinstance(x, dict) and x.get("code")}
            verification = {"health_score_before": before_score, "health_score_after": after_score, "improved": after_score > before_score, "unchanged": after_score == before_score, "effective": after_score > before_score or bool(before_codes - after_codes), "remaining_issues": after["diagnoses"], "advanced_after": after.get("advanced")}
        self.db.action(dt.datetime.now(dt.timezone.utc).isoformat(), f"network:{action}", "network", "ok" if result.get("ok") else ("skipped:" + str(result.get("reason", "unknown"))))
        return {"before": before, "result": result, "after": after, "verification": verification}

    def restore(self, token: str):
        return restore(self.data / "quarantine", token)
