from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path


def find_duplicates(root: str | Path, max_files: int = 5000, min_size: int = 1024 * 1024) -> list[list[str]]:
    """Find duplicate files by size and SHA-256; read-only and bounded."""
    root = Path(root)
    by_size: dict[int, list[Path]] = defaultdict(list)
    seen = 0
    if not root.is_dir():
        return []
    for p in root.rglob("*"):
        if seen >= max_files:
            break
        try:
            if p.is_file() and not p.is_symlink():
                size = p.stat().st_size
                if size >= min_size:
                    by_size[size].append(p)
                    seen += 1
        except (OSError, PermissionError):
            continue
    groups = []
    for paths in by_size.values():
        if len(paths) < 2:
            continue
        hashes: dict[str, list[str]] = defaultdict(list)
        for p in paths:
            try:
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                hashes[h.hexdigest()].append(str(p))
            except (OSError, PermissionError):
                continue
        groups.extend(v for v in hashes.values() if len(v) > 1)
    return groups
