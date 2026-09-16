import time

from smartpc.db import DB


def test_maintenance_lease_is_single_instance(tmp_path):
    db = DB(tmp_path / "smartpc.db")
    assert db.try_acquire_maintenance("first", lease_seconds=60)
    assert not db.try_acquire_maintenance("second", lease_seconds=60)
    db.release_maintenance("first")
    assert db.try_acquire_maintenance("second", lease_seconds=60)
    db.release_maintenance("second")


def test_expired_maintenance_lease_can_be_reclaimed(tmp_path):
    db = DB(tmp_path / "smartpc.db")
    assert db.try_acquire_maintenance("first", lease_seconds=1)
    time.sleep(1.1)
    assert db.try_acquire_maintenance("second", lease_seconds=60)
    db.release_maintenance("second")


def test_maintenance_budget_is_accounted(tmp_path):
    db = DB(tmp_path / "smartpc.db")
    now = time.time()
    db.maintenance_run(now - 10, now - 5, "disk_pressure", 2, 100, 8.0, 9.0, "ok")
    db.maintenance_run(now - 2, now - 1, "predictive_pressure", 1, 50, 9.0, 9.5, "ok")
    assert db.maintenance_bytes_since(now - 60) == 150
    assert db.last_maintenance()[3] == 50
