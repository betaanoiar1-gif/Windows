from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_ALLOWED = {"keep", "review", "quarantine"}
_MAX_ACTIONS = 50
_MAX_ITEMS = 20
_MAX_TEXT = 1000


def _safe_text(value: Any, limit: int = _MAX_TEXT) -> str:
    return str(value or "")[:limit]


def _safe_timeout(value: Any, default: int = 30) -> int:
    try:
        return max(5, min(120, int(value)))
    except (TypeError, ValueError):
        return default


class AIClient:
    """OpenAI-compatible advisory client; local safety remains authoritative."""

    def __init__(self, base_url=None, model=None, timeout=None):
        self.base_url = (base_url or os.getenv("AI_BASE_URL", "")).strip().rstrip("/")
        self.model = (model or os.getenv("AI_MODEL", "")).strip()
        self.key = (os.getenv("AI_API_KEY", "") or "").strip()
        self.timeout = _safe_timeout(timeout if timeout is not None else os.getenv("SMARTPC_AI_TIMEOUT", "30"))

    @property
    def enabled(self):
        return bool(self.base_url and self.model and self.key)

    def analyze(self, payload: dict[str, Any]):
        if not self.enabled:
            return {"mode": "local", "observations": [], "recommendations": [], "actions": [], "message": "AI API not configured"}
        system = (
            "You are a Windows optimization analyst. Return JSON only. "
            "Allowed actions are keep, review, quarantine. Never request shell commands, registry edits, "
            "service changes, process termination, driver changes, network repairs, or permanent deletion. "
            "Every action must reference a supplied candidate_id."
        )
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read())
            choices = raw.get("choices") if isinstance(raw, dict) else None
            message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
            text = message.get("content", "") if isinstance(message, dict) else ""
            if isinstance(text, list):
                text = "".join(str(x.get("text", "")) for x in text if isinstance(x, dict))
            parsed = json.loads(text) if isinstance(text, str) else text
            return self._validate(parsed, payload)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError, TypeError, KeyError, IndexError) as exc:
            return {"mode": "ai_error", "observations": [], "recommendations": [], "actions": [], "message": f"AI request failed safely: {type(exc).__name__}"}

    def _validate(self, value: Any, payload: dict[str, Any]):
        if not isinstance(value, dict):
            return {"mode": "ai_invalid", "observations": [], "recommendations": [], "actions": [], "message": "AI returned a non-object"}
        raw_candidates = payload.get("candidates", [])
        valid_ids = {str(c.get("candidate_id")) for c in raw_candidates if isinstance(c, dict) and c.get("candidate_id") is not None}
        raw_actions = value.get("actions", [])
        actions: list[dict[str, Any]] = []
        if isinstance(raw_actions, list):
            for item in raw_actions[: _MAX_ACTIONS * 2]:
                if not isinstance(item, dict):
                    continue
                cid = str(item.get("candidate_id", ""))
                act = str(item.get("action", "review")).strip().lower()
                if cid not in valid_ids or act not in _ALLOWED:
                    continue
                try:
                    conf = max(0.0, min(1.0, float(item.get("confidence", 0))))
                except (TypeError, ValueError):
                    conf = 0.0
                actions.append({
                    "candidate_id": cid,
                    "action": act,
                    "confidence": conf,
                    "reason": _safe_text(item.get("reason", ""), 500),
                })
                if len(actions) >= _MAX_ACTIONS:
                    break
        observations = value.get("observations", [])
        recommendations = value.get("recommendations", [])
        if not isinstance(observations, list):
            observations = []
        if not isinstance(recommendations, list):
            recommendations = []
        return {
            "mode": "ai",
            "observations": [_safe_text(x) for x in observations[:_MAX_ITEMS]],
            "recommendations": [_safe_text(x) for x in recommendations[:_MAX_ITEMS]],
            "actions": actions,
            "message": "Validated advisory response",
        }
