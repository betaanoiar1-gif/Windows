from pathlib import Path
from smartpc.models import Candidate, Action
from smartpc.storage import safe_quarantine, restore


def test_quarantine_and_restore(tmp_path):
    source = tmp_path / "temp" / "demo.tmp"
    source.parent.mkdir()
    source.write_bytes(b"safe test data")
    q = tmp_path / "quarantine"
    c = Candidate(str(source), "temporary", source.stat().st_size, 2, action=Action.QUARANTINE)
    moved = safe_quarantine([c], q)
    assert len(moved) == 1
    token = moved[0][2]
    assert not source.exists()
    restored = restore(q, token)
    assert Path(restored) == source
    assert source.read_bytes() == b"safe test data"


def test_restore_refuses_overwrite(tmp_path):
    source = tmp_path / "a.tmp"
    source.write_text("original", encoding="utf-8")
    q = tmp_path / "q"
    c = Candidate(str(source), "temporary", 8, 1, action=Action.QUARANTINE)
    token = safe_quarantine([c], q)[0][2]
    source.write_text("new", encoding="utf-8")
    import pytest
    with pytest.raises(FileExistsError):
        restore(q, token)
