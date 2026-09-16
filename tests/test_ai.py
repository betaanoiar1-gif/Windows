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


def test_ai_validator_handles_malformed_lists_and_caps_output():
    c = AIClient(timeout="not-a-number")
    payload = {"candidates": [{"candidate_id": str(i)} for i in range(60)]}
    result = c._validate({
        "observations": "not-a-list",
        "recommendations": None,
        "actions": [{"candidate_id": str(i), "action": "review", "confidence": "bad"} for i in range(60)],
    }, payload)
    assert len(result["actions"]) == 50
    assert all(x["confidence"] == 0.0 for x in result["actions"])
    assert c.timeout == 30
