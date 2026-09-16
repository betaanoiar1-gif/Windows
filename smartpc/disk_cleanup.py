from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from .models import Action, Candidate, Risk
from .safety import is_protected


@dataclass(frozen=True)
class CleanupCategory:
    key: str
    name: str
    description: str
    risk: Risk
    automatic: bool
    paths: tuple[Path, ...]

    def to_dict(self):
        return {
            **asdict(self),
            "risk": self.risk.value,
            "paths": [str(p) for p in self.paths],
        }


def _existing(*values: str | Path | None) -> tuple[Path, ...]:
    out = []
    seen = set()
    for value in values:
        if not value:
            continue
        p = Path(value)
        key = str(p).lower()
        if p.is_dir() and key not in seen:
            seen.add(key)
            out.append(p)
    return tuple(out)


def categories() -> list[CleanupCategory]:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    local = os.environ.get("LOCALAPPDATA")
    program_data = os.environ.get("ProgramData")
    user_profile = os.environ.get("USERPROFILE")
    return [
        CleanupCategory(
            "temp", "User/System temporary files",
            "Temporary files left by applications and Windows; safe candidates are quarantined rather than permanently deleted.",
            Risk.SAFE, True, _existing(tempfile.gettempdir(), Path(local or "") / "Temp"),
        ),
        CleanupCategory(
            "windows_update_download", "Windows Update download cache",
            "Downloaded update payloads that Windows can recreate when required. Active/locked files are skipped.",
            Risk.LOW, False, _existing(Path(windir) / "SoftwareDistribution" / "Download"),
        ),
        CleanupCategory(
            "delivery_optimization", "Delivery Optimization cache",
            "Windows peer/content-delivery cache. It can be rebuilt; intentional active files are left untouched.",
            Risk.LOW, False, _existing(Path(program_data or "") / "Microsoft" / "Windows" / "DeliveryOptimization" / "Cache"),
        ),
        CleanupCategory(
            "wer", "Windows Error Reporting leftovers",
            "Old crash/error reports retained after diagnostics. Recent reports are kept for troubleshooting.",
            Risk.LOW, False, _existing(Path(program_data or "") / "Microsoft" / "Windows" / "WER" / "ReportArchive", Path(program_data or "") / "Microsoft" / "Windows" / "WER" / "ReportQueue"),
        ),
        CleanupCategory(
            "minidumps", "Crash dump files",
            "Old user/kernel minidumps. Useful for debugging, so they are review-only unless explicitly selected.",
            Risk.LOW, False, _existing(Path(windir) / "Minidump", Path(user_profile or "") / "AppData" / "Local" / "CrashDumps"),
        ),
        CleanupCategory(
            "directx_shader_cache", "DirectX shader cache",
            "Rebuildable graphics shader cache; deleting it may cause temporary shader recompilation.",
            Risk.LOW, False, _existing(Path(local or "") / "D3DSCache"),
        ),
        CleanupCategory(
            "explorer_thumbnails", "Explorer thumbnail cache",
            "Rebuildable thumbnail databases. Windows recreates thumbnails as folders are browsed.",
            Risk.LOW, False, _existing(Path(local or "") / "Microsoft" / "Windows" / "Explorer"),
        ),
    ]


def _walk_files(root: Path, max_files: int, followlinks: bool = False) -> Iterable[Path]:
    if not root.is_dir():
        return
    count = 0
    try:
        for base, dirs, files in os.walk(root, topdown=True, followlinks=followlinks):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(base, d))]
            for name in files:
                if count >= max_files:
                    return
                p = Path(base) / name
                if p.is_symlink() or is_protected(str(p)):
                    continue
                try:
                    if p.is_file():
                        count += 1
                        yield p
                except OSError:
                    continue
    except (OSError, PermissionError):
        return


def _age_days(path: Path) -> float:
    try:
        return max(0.0, (time.time() - path.stat().st_mtime) / 86400.0)
    except OSError:
        return 0.0


def _matches_category(category: CleanupCategory, path: Path) -> bool:
    if category.key == "explorer_thumbnails":
        return path.name.lower().startswith("thumbcache_") and path.suffix.lower() == ".db"
    return True


def scan_deep(max_files: int = 30000, min_age_days: float = 1.0) -> list[Candidate]:
    """Build a bounded, evidence-based inventory of reclaimable C: drive data.

    This is intentionally a scanner, not a blind deleter. System caches are review-only;
    only ordinary temporary data is eligible for the existing reversible quarantine path.
    """
    max_files = max(100, min(int(max_files), 100000))
    min_age_days = max(0.0, min(float(min_age_days), 3650.0))
    result: list[Candidate] = []
    seen: set[str] = set()
    per_category = max(100, max_files // max(1, len(categories())))

    for category in categories():
        for root in category.paths:
            for path in _walk_files(root, per_category):
                key = str(path.resolve()).lower()
                if key in seen:
                    continue
                seen.add(key)
                age = _age_days(path)
                if age < min_age_days or not _matches_category(category, path):
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                action = Action.QUARANTINE if category.automatic else Action.REVIEW
                result.append(Candidate(
                    target=str(path), kind=f"cleanup:{category.key}", size=size, age_days=age,
                    risk=category.risk, action=action,
                    reason=category.description, reversible=category.automatic,
                    metadata={"category": category.key, "category_name": category.name, "root": str(root)},
                ))
                if len(result) >= max_files:
                    return sorted(result, key=lambda x: x.size, reverse=True)
    return sorted(result, key=lambda x: x.size, reverse=True)


def summarize(candidates: list[Candidate]) -> dict:
    by_category: dict[str, dict] = {}
    for c in candidates:
        key = str(c.metadata.get("category", c.kind))
        row = by_category.setdefault(key, {"files": 0, "bytes": 0, "risk": c.risk.value, "action": c.action.value})
        row["files"] += 1
        row["bytes"] += max(0, c.size)
    total = sum(max(0, c.size) for c in candidates)
    automatic = sum(max(0, c.size) for c in candidates if c.action is Action.QUARANTINE)
    return {
        "files": len(candidates),
        "bytes": total,
        "gb": round(total / 1024**3, 3),
        "automatic_quarantine_bytes": automatic,
        "automatic_quarantine_gb": round(automatic / 1024**3, 3),
        "categories": by_category,
    }
