from smartpc.ai import AIClient


def test_ai_is_disabled_without_credentials(monkeypatch):
    for k in ("AI_API_KEY", "AI_BASE_URL", "AI_MODEL"):
        monkeypatch.delenv(k, raising=False)
    assert not AIClient().enabled
    assert AIClient().analyze({})["mode"] == "local"


def test_ai_validator_rejects_unknown_targets_and_dangerous_actions():
    c = AIClient()
    payload = {"candidates": [{"candidate_id": "1"}]}
    result = c._validate({"actions": [
        {"candidate_id": "1", "action": "delete", "confidence": 1},
        {"candidate_id": "999", "action": "quarantine", "confidence": 1},
        {"candidate_id": "1", "action": "quarantine", "confidence": 0.8},
    ]}, payload)
    assert len(result["actions"]) == 1
    assert result["actions"][0]["candidate_id"] == "1"
