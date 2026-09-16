from pathlib import Path

from smartpc.models import Action, Candidate, Risk
from smartpc.storage import safe_quarantine


def _candidate(path: Path, size: int):
    return Candidate(
        str(path), "temporary", size, 10.0, Risk.SAFE,
        Action.QUARANTINE, "test", True, {}
    )


def test_quarantine_enforces_file_budget(tmp_path):
    source = tmp_path / "a.tmp"
    source.write_bytes(b"a")
    moved = safe_quarantine([_candidate(source, 1)], tmp_path / "q", limit=0)
    assert moved == []
    assert source.exists()


def test_quarantine_enforces_byte_budget(tmp_path):
    source = tmp_path / "large.tmp"
    source.write_bytes(b"12345")
    moved = safe_quarantine([_candidate(source, 5)], tmp_path / "q", limit=10, max_bytes=4)
    assert moved == []
    assert source.exists()
