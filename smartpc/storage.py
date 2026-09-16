import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from .models import Candidate, Action, Risk


def _age_days(path: Path) -> float:
    try:
        return max(0.0, (time.time() - path.stat().st_mtime) / 86400)
    except OSError:
        return 0.0


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def scan_temp(max_files: int = 10000) -> list[Candidate]:
    roots = {Path(tempfile.gettempdir())}
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.add(Path(local) / "Temp")
    out: list[Candidate] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(base, d))]
                for name in files:
                    if len(out) >= max_files:
                        return out
                    p = Path(base) / name
                    try:
                        if not _under(p, root) or not p.is_file() or p.is_symlink():
                            continue
                        key = str(p.resolve()).lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        s = p.stat().st_size
                        out.append(Candidate(str(p), "temporary", s, _age_days(p), Risk.SAFE, Action.REVIEW, "Temporary-directory file; reversible quarantine candidate", True, {"root": str(root)}))
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            continue
    return out


def hash_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_quarantine(candidates, quarantine: Path, limit: int = 50, max_bytes: int = 512 * 1024 * 1024):
    """Move only authorized candidates within strict per-cycle file/byte budgets."""
    quarantine.mkdir(parents=True, exist_ok=True)
    manifest = quarantine / "manifest.jsonl"
    moved = []
    moved_bytes = 0
    for c in candidates:
        if len(moved) >= max(0, limit) or moved_bytes >= max(0, max_bytes):
            break
        src = Path(c.target)
        size = max(0, int(c.size))
        if c.action != Action.QUARANTINE or not src.is_file() or src.is_symlink():
            continue
        if size > max_bytes - moved_bytes:
            continue
        try:
            token = hashlib.sha256(f"{src.resolve()}|{time.time_ns()}".encode()).hexdigest()[:24]
            dest = quarantine / f"{token}_{src.name}"
            shutil.move(str(src), str(dest))
            record = {"id": token, "original": str(src), "quarantined": str(dest), "ts": time.time(), "size": size}
            with manifest.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            moved.append((str(src), str(dest), token))
            moved_bytes += size
        except (OSError, PermissionError, shutil.Error):
            continue
    return moved


def restore(quarantine: Path, token: str) -> str:
    manifest = quarantine / "manifest.jsonl"
    if not manifest.exists():
        raise FileNotFoundError("Quarantine manifest not found")
    records = [json.loads(x) for x in manifest.read_text(encoding="utf-8").splitlines() if x.strip()]
    match = next((r for r in reversed(records) if r.get("id") == token), None)
    if not match:
        raise KeyError(token)
    src, original = Path(match["quarantined"]), Path(match["original"])
    if not src.is_file():
        raise FileNotFoundError(str(src))
    if original.exists():
        raise FileExistsError(str(original))
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(original))
    return str(original)
