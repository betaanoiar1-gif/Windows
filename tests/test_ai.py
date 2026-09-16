from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

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


def test_ai_provider_round_trip_uses_validated_advisory_only(monkeypatch):
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received["body"] = json.loads(self.rfile.read(length))
            received["auth"] = self.headers.get("Authorization")
            response = {
                "choices": [{"message": {"content": json.dumps({
                    "observations": ["candidate appears stale"],
                    "recommendations": ["review before cleanup"],
                    "actions": [
                        {"candidate_id": "safe-1", "action": "quarantine", "confidence": 0.9},
                        {"candidate_id": "safe-1", "action": "delete", "confidence": 1.0},
                        {"candidate_id": "unknown", "action": "quarantine", "confidence": 1.0},
                    ],
                })}}]
            }
            data = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.setenv("AI_BASE_URL", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("AI_MODEL", "mock-model")
        client = AIClient(timeout=5)
        payload = {"candidates": [{"candidate_id": "safe-1"}]}
        result = client.analyze(payload)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert received["auth"] == "Bearer test-key"
    assert received["body"]["model"] == "mock-model"
    assert result["mode"] == "ai"
    assert result["actions"] == [{
        "candidate_id": "safe-1",
        "action": "quarantine",
        "confidence": 0.9,
        "reason": "",
    }]
