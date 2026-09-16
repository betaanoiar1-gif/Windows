import os
from dataclasses import dataclass
from pathlib import Path


def _int_env(name: str, default: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _float_env(name: str, default: float, minimum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    # Safe autonomous maintenance is enabled by default. It only operates on
    # locally-authorized temporary files and uses reversible quarantine.
    auto_safe_cleanup: bool = True
    auto_cleanup_free_percent: float = 10.0
    auto_cleanup_free_gb: float = 15.0
    max_scan_files: int = 10000
    max_quarantine_files: int = 5000
    ai_timeout_seconds: int = 30

    @classmethod
    def load(cls, data_dir: str | None = None) -> "Settings":
        if data_dir:
            root = Path(data_dir)
        elif os.name == "nt":
            root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "SmartPCAI"
        else:
            root = Path.home() / ".smartpc-ai"
        return cls(
            data_dir=root,
            auto_safe_cleanup=os.getenv("SMARTPC_AUTO_SAFE_CLEANUP", "1") == "1",
            auto_cleanup_free_percent=_float_env("SMARTPC_AUTO_CLEANUP_FREE_PERCENT", 10.0, 1.0),
            auto_cleanup_free_gb=_float_env("SMARTPC_AUTO_CLEANUP_FREE_GB", 15.0, 1.0),
            max_scan_files=_int_env("SMARTPC_MAX_SCAN_FILES", 10000, 100),
            max_quarantine_files=_int_env("SMARTPC_MAX_QUARANTINE_FILES", 5000, 1),
            ai_timeout_seconds=_int_env("SMARTPC_AI_TIMEOUT", 30, 5),
        )
