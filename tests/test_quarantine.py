from pathlib import Path

from smartpc.quarantine import QuarantineStore


def test_quarantine_roundtrip(tmp_path: Path):
    source = tmp_path / "sample.tmp"
    source.write_text("safe test data", encoding="utf-8")
    store = QuarantineStore(tmp_path / "q")
    record = store.put(source)
    assert not source.exists()
    assert Path(record["quarantined"]).exists()
    store.restore(record["id"])
    assert source.read_text(encoding="utf-8") == "safe test data"
