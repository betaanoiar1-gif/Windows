from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path


class QuarantineStore:
    """Reversible file quarantine. It never overwrites an existing quarantined item."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.items = self.root / "items"
        self.manifest = self.root / "manifest.jsonl"
        self.items.mkdir(parents=True, exist_ok=True)

    def put(self, source: str | Path) -> dict:
        src = Path(source)
        if not src.is_file():
            raise FileNotFoundError(src)
        token = uuid.uuid4().hex
        dst = self.items / f"{token}__{src.name}"
        shutil.move(str(src), str(dst))
        record = {
            "id": token,
            "original": str(src),
            "quarantined": str(dst),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self.manifest.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def list_items(self) -> list[dict]:
        if not self.manifest.exists():
            return []
        rows = []
        for line in self.manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def restore(self, item_id: str) -> dict:
        for record in reversed(self.list_items()):
            if record["id"] != item_id:
                continue
            src = Path(record["quarantined"])
            dst = Path(record["original"])
            if not src.is_file():
                raise FileNotFoundError(src)
            if dst.exists():
                raise FileExistsError(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return record
        raise KeyError(item_id)
