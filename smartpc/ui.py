import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
from .engine import Engine
from .windows import install_startup_task, remove_startup_task, startup_status

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SMARTPC AI")
        self.resize(820, 600)
        self.engine = Engine()
        w = QWidget(); layout = QVBoxLayout(w)
        self.status = QLabel("Ready — local safety mode; AI is optional")
        self.output = QTextEdit(); self.output.setReadOnly(True)
        scan = QPushButton("Analyze System"); scan.clicked.connect(self.inspect)
        clean = QPushButton("Safe Optimize (Quarantine Only)"); clean.clicked.connect(self.optimize)
        startup = QPushButton("Install Observation at Windows Logon"); startup.clicked.connect(self.install_startup)
        remove = QPushButton("Remove Logon Task"); remove.clicked.connect(self.remove_startup)
        for x in (self.status, scan, clean, startup, remove, self.output): layout.addWidget(x)
        self.setCentralWidget(w)

    def inspect(self):
        try:
            r = self.engine.inspect()
            s = r["snapshot"]
            total = sum(x.size for x in r["candidates"]) / 1024**3
            lines = [f"CPU: {s.cpu_percent:.1f}% | RAM: {s.ram_percent:.1f}% | Disk: {s.disk_percent:.1f}% | Free: {s.disk_free_gb:.1f} GB", f"Temporary candidates: {len(r['candidates'])} | Potential data: {total:.2f} GB", "", "DIAGNOSES:"]
            lines += [f"- {d.title}: {'; '.join(d.evidence)}" for d in r["diagnoses"]] or ["- No threshold anomaly detected."]
            lines += ["", f"AI: {r['ai'].get('mode')} — {r['ai'].get('message','')}", "No changes made."]
            self.status.setText("Analysis complete")
            self.output.setPlainText("\n".join(lines))
        except Exception as exc:
            self.status.setText("Analysis failed safely")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")

    def optimize(self):
        try:
            r = self.engine.optimize_safe(); b, a = r["before"], r["after"]
            self.status.setText("Safe quarantine complete")
            self.output.setPlainText(f"Quarantined: {len(r['moved'])} files\nBefore free disk: {b.disk_free_gb:.2f} GB\nAfter free disk: {a.disk_free_gb:.2f} GB\nBefore RAM: {b.ram_percent:.1f}%\nAfter RAM: {a.ram_percent:.1f}%\n\nPermanent deletion: never used.")
        except Exception as exc:
            self.status.setText("Optimization failed safely")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")

    def install_startup(self):
        try:
            install_startup_task(); self.status.setText("Observation startup task installed")
        except Exception as exc: self.output.setPlainText(f"{type(exc).__name__}: {exc}")

    def remove_startup(self):
        try:
            remove_startup_task(); self.status.setText("Startup task removed/requested")
        except Exception as exc: self.output.setPlainText(f"{type(exc).__name__}: {exc}")

def run():
    app = QApplication(sys.argv); win = MainWindow(); win.show(); return app.exec()
