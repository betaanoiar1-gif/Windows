import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    data_dir: Path
    auto_safe_cleanup: bool = False
    max_scan_files: int = 10000
    max_quarantine_files: int = 5000
    ai_timeout_seconds: int = 30

    @classmethod
    def load(cls, data_dir: str | None = None) -> "Settings":
        if data_dir:
            root = Path(data_dir)
        elif os.name == "nt":
            root = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SmartPCAI"
        else:
            root = Path.home() / ".smartpc-ai"
        return cls(
            data_dir=root,
            auto_safe_cleanup=os.getenv("SMARTPC_AUTO_SAFE_CLEANUP", "0") == "1",
            max_scan_files=max(100, int(os.getenv("SMARTPC_MAX_SCAN_FILES", "10000"))),
            max_quarantine_files=max(1, int(os.getenv("SMARTPC_MAX_QUARANTINE_FILES", "5000"))),
            ai_timeout_seconds=max(5, int(os.getenv("SMARTPC_AI_TIMEOUT", "30"))),
        )
