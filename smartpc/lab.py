from pathlib import Path
import os


def create_fixtures(root: str, count: int = 12) -> Path:
    """Create harmless test files only inside the caller-provided lab directory."""
    base = Path(root).resolve()
    base.mkdir(parents=True, exist_ok=True)
    marker = base / ".smartpc-lab"
    marker.write_text("SMARTPC AI disposable laboratory\n", encoding="utf-8")
    for i in range(max(1, min(count, 100))):
        p = base / f"fixture_{i:03d}.tmp"
        p.write_bytes(os.urandom(1024 + i * 17))
    return base
