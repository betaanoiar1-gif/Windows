from smartpc.config import Settings


def test_invalid_environment_values_fall_back_safely(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTPC_MAX_SCAN_FILES", "invalid")
    monkeypatch.setenv("SMARTPC_MAX_QUARANTINE_FILES", "-10")
    monkeypatch.setenv("SMARTPC_AI_TIMEOUT", "oops")
    settings = Settings.load(str(tmp_path))
    assert settings.data_dir == tmp_path
    assert settings.max_scan_files == 10000
    assert settings.max_quarantine_files == 1
    assert settings.ai_timeout_seconds == 30


def test_configuration_bounds_are_enforced(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTPC_MAX_SCAN_FILES", "50")
    monkeypatch.setenv("SMARTPC_MAX_QUARANTINE_FILES", "0")
    monkeypatch.setenv("SMARTPC_AI_TIMEOUT", "1")
    settings = Settings.load(str(tmp_path))
    assert settings.max_scan_files == 100
    assert settings.max_quarantine_files == 1
    assert settings.ai_timeout_seconds == 5
