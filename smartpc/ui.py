import sys
from PySide6.QtWidgets import QApplication,QMainWindow,QVBoxLayout,QLabel,QPushButton,QTextEdit,QWidget
from .engine import Engine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("SMARTPC AI"); self.resize(760,520); self.engine=Engine()
        w=QWidget(); l=QVBoxLayout(w); self.status=QLabel("Ready — no AI key configured")
        self.output=QTextEdit(); self.output.setReadOnly(True)
        scan=QPushButton("Analyze System"); scan.clicked.connect(self.inspect)
        clean=QPushButton("Safe Optimize (Quarantine)"); clean.clicked.connect(self.optimize)
        l.addWidget(self.status); l.addWidget(scan); l.addWidget(clean); l.addWidget(self.output); self.setCentralWidget(w)
    def inspect(self):
        s,c=self.engine.inspect(); self.status.setText(f"CPU {s.cpu_percent:.0f}%  | RAM {s.ram_percent:.0f}%  | Disk {s.disk_percent:.0f}%  | Free {s.disk_free_gb:.1f} GB")
        total=sum(x.size for x in c)/1024**3; self.output.setPlainText(f"Temporary candidates: {len(c)}\nPotential data: {total:.2f} GB\n\nNo changes made.")
    def optimize(self):
        b,a,m=self.engine.optimize_safe(); self.output.setPlainText(f"Quarantined: {len(m)} files\nBefore RAM: {b.ram_percent:.1f}%\nAfter RAM: {a.ram_percent:.1f}%\nBefore free disk: {b.disk_free_gb:.2f} GB\nAfter free disk: {a.disk_free_gb:.2f} GB")

def run():
    app=QApplication(sys.argv); win=MainWindow(); win.show(); return app.exec()
