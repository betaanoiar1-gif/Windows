import sys

from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QLabel, QPushButton, QTextEdit, QWidget

from .engine import Engine
from .windows import install_startup_task, maintenance_status, remove_startup_task, startup_status


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMARTPC AI")
        self.resize(980, 720)
        self.engine = Engine()
        root = QWidget()
        layout = QVBoxLayout(root)
        self.status = QLabel(self._startup_text())
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        row1 = QHBoxLayout()
        for label, handler in (("Analyze System", self.inspect), ("Deep C: Scan", self.deep_scan), ("Diagnose Network", self.network), ("Show Repair Plan", self.network_plan), ("Safe Optimize", self.optimize), ("Run Autonomous Cycle", self.maintenance)):
            button = QPushButton(label)
            button.clicked.connect(handler)
            row1.addWidget(button)
        row2 = QHBoxLayout()
        for label, handler in (("Install Autonomous Startup", self.install_startup), ("Remove Autonomous Startup", self.remove_startup)):
            button = QPushButton(label)
            button.clicked.connect(handler)
            row2.addWidget(button)
        for item in (self.status, row1, row2, self.output):
            layout.addWidget(item)
        self.setCentralWidget(root)

    @staticmethod
    def _startup_text():
        try:
            return f"Autonomous startup: {'ON' if startup_status() else 'OFF'} | 30-minute maintenance: {'ON' if maintenance_status() else 'OFF'} | AI optional"
        except Exception:
            return "Ready — autonomous safe maintenance available; AI is optional"

    def _show_error(self, prefix, exc):
        self.status.setText(prefix)
        self.output.setPlainText(f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _gb(value):
        return value / 1024**3

    def inspect(self):
        try:
            r = self.engine.inspect()
            s = r["snapshot"]
            total = sum(x.size for x in r["candidates"]) / 1024**3
            n = r["network_health"]
            d = r["disk_cleanup"]
            lines = [
                f"SYSTEM  CPU {s.cpu_percent:.1f}% | RAM {s.ram_percent:.1f}% | Disk {s.disk_percent:.1f}% | Free {s.disk_free_gb:.1f} GB",
                f"HEALTH  {r['health_score']}/100 | Temporary candidates {len(r['candidates'])} | Potential temp data {total:.2f} GB",
                f"DISK CLEANUP  {d['gb']:.2f} GB identified | {d['automatic_quarantine_gb']:.2f} GB reversible-safe candidates",
                f"NETWORK {n.state} | {n.score:.0f}/100 | Active interfaces {n.active_interfaces}",
                "",
                "DIAGNOSES:",
            ]
            lines += [f"- {x.title}: {'; '.join(x.evidence)}" for x in r["diagnoses"]] or ["- No system threshold anomaly detected."]
            lines += ["", "NETWORK DIAGNOSES:"]
            lines += [f"- {x.get('title', x.get('code', 'issue'))}: {'; '.join(map(str, x.get('evidence', [])))}" for x in r["network_diagnoses"]] or ["- No network issue detected by the current probes."]
            lines += ["", f"AI: {r['ai'].get('mode')} — {r['ai'].get('message', '')}", "No changes made by analysis."]
            self.status.setText("Analysis complete")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self._show_error("Analysis failed safely", exc)

    def deep_scan(self):
        try:
            r = self.engine.deep_disk_scan()
            s = r["summary"]
            lines = [
                "SMARTPC DEEP C: DRIVE CLEANUP",
                "",
                f"Reclaimable/review inventory: {s['gb']:.3f} GB across {s['files']} files",
                f"Automatically quarantine-eligible: {s['automatic_quarantine_gb']:.3f} GB",
                "",
                "CATEGORIES:",
            ]
            for key, row in sorted(s["categories"].items(), key=lambda item: item[1]["bytes"], reverse=True):
                lines.append(f"- {key}: {self._gb(row['bytes']):.3f} GB | {row['files']} files | risk={row['risk']} | action={row['action']}")
            lines += ["", "Important: system caches are review-only. SMARTPC never permanently deletes them automatically."]
            self.status.setText("Deep C: scan complete — nothing changed")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self._show_error("Deep disk scan failed safely", exc)

    def network(self):
        try:
            r = self.engine.network_inspect(probes=True)
            n, c = r["health"], r["connectivity"]
            lines = [f"NETWORK HEALTH: {n.state} — {n.score:.0f}/100", f"Connectivity: {c.state if c else 'unknown'}", f"Active interfaces: {n.active_interfaces}", f"Gateway latency: {n.gateway_latency_ms} ms", f"DNS latency: {n.dns_latency_ms} ms", "", "EVIDENCE:"]
            lines += [f"- {x}" for x in n.evidence] or ["- No negative health evidence."]
            lines += ["", "ADVANCED HTTPS:"]
            summary = (r.get("advanced") or {}).get("https_summary") or {}
            lines.append(f"- {summary.get('successful', 0)}/{summary.get('targets', 0)} HTTPS endpoints reachable")
            self.status.setText("Network diagnosis complete")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self._show_error("Network diagnosis failed safely", exc)

    def network_plan(self):
        try:
            r = self.engine.network_inspect(probes=True)
            lines = ["RECOVERY PLAN — no action executed", ""]
            if not r["recovery_plan"]:
                lines.append("No evidence-backed automatic repair is recommended.")
            for step in r["recovery_plan"]:
                lines.append(f"- {step['action']} | risk={step['risk']} | admin={step['requires_admin']} | reboot={step['requires_reboot']} | {step['reason']}")
            self.status.setText("Repair plan generated — nothing changed")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self._show_error("Repair plan failed safely", exc)

    def optimize(self):
        try:
            r = self.engine.optimize_safe()
            b, a = r["before"], r["after"]
            self.status.setText("Safe quarantine complete")
            self.output.setPlainText(f"Quarantined: {len(r['moved'])} files\nBefore free disk: {b.disk_free_gb:.2f} GB\nAfter free disk: {a.disk_free_gb:.2f} GB\nBefore RAM: {b.ram_percent:.1f}%\nAfter RAM: {a.ram_percent:.1f}%\n\nPermanent deletion: never used.")
        except Exception as exc:
            self._show_error("Optimization failed safely", exc)

    def maintenance(self):
        try:
            r = self.engine.autonomous_maintenance()
            p, pred, after = r["pressure_before"], r["prediction"], r["pressure_after"]
            lines = [
                "AUTONOMOUS MAINTENANCE",
                "",
                f"Trigger: {'YES' if r['triggered'] else 'NO'}",
                f"C: free before {p['free_gb']:.2f} GB ({p['free_percent']:.1f}%)",
                f"Prediction: {pred['reason']}",
                f"Measured consumption: {pred['rate_gb_per_hour']:.3f} GB/hour",
                f"Projected free space: {pred['projected_free_gb'] if pred['projected_free_gb'] is not None else 'n/a'} GB",
                f"Quarantined: {len(r['moved'])} file(s)",
                f"C: free after {after['free_gb']:.2f} GB ({after['free_percent']:.1f}%)",
            ]
            if r["skipped_reason"]:
                lines += ["", f"Skipped/rollback reason: {r['skipped_reason']}"]
            lines += ["", "Only reversible temporary-file quarantine is permitted in unattended mode."]
            self.status.setText("Autonomous cycle complete")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self._show_error("Autonomous maintenance failed safely", exc)

    def install_startup(self):
        try:
            install_startup_task()
            self.status.setText(self._startup_text())
            self.output.setPlainText("SMARTPC AI will observe at Windows logon and run bounded safe maintenance every 30 minutes.\n\nAutomatic mutation is limited to reversible temporary-file quarantine when the system drive is under pressure.\nNetwork repairs, registry changes, service changes, driver changes and permanent deletion remain manual.")
        except Exception as exc:
            self._show_error("Autonomous startup installation failed", exc)

    def remove_startup(self):
        try:
            remove_startup_task()
            self.status.setText(self._startup_text())
            self.output.setPlainText("Autonomous startup and scheduled maintenance were removed/requested.")
        except Exception as exc:
            self._show_error("Startup removal failed", exc)


def run():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()
