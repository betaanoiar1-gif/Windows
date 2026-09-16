import json
import os
import urllib.error
import urllib.request

_ALLOWED = {"keep", "review", "quarantine"}

class AIClient:
    """OpenAI-compatible advisory client; local safety remains authoritative."""
    def __init__(self, base_url=None, model=None, timeout=None):
        self.base_url = (base_url or os.getenv("AI_BASE_URL", "")).rstrip("/")
        self.model = model or os.getenv("AI_MODEL", "")
        self.key = os.getenv("AI_API_KEY", "")
        self.timeout = int(timeout or os.getenv("SMARTPC_AI_TIMEOUT", "30"))

    @property
    def enabled(self):
        return bool(self.base_url and self.model and self.key)

    def analyze(self, payload):
        if not self.enabled:
            return {"mode":"local", "observations":[], "recommendations":[], "actions":[], "message":"AI API not configured"}
        system = ("You are a Windows optimization analyst. Return JSON only. "
                  "Allowed actions are keep, review, quarantine. Never request shell commands, registry edits, service changes, process termination, driver changes, or permanent deletion. Every action must reference a supplied candidate_id.")
        body = json.dumps({"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(payload)}],"temperature":0.1}).encode()
        req = urllib.request.Request(self.base_url+"/chat/completions", data=body, headers={"Content-Type":"application/json","Authorization":"Bearer "+self.key}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = json.loads(r.read())
            text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(text) if isinstance(text, str) else text
            return self._validate(parsed, payload)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError, IndexError) as exc:
            return {"mode":"ai_error","observations":[],"recommendations":[],"actions":[],"message":f"AI request failed safely: {type(exc).__name__}"}

    def _validate(self, value, payload):
        if not isinstance(value, dict):
            return {"mode":"ai_invalid","observations":[],"recommendations":[],"actions":[],"message":"AI returned a non-object"}
        valid_ids = {str(c.get("candidate_id")) for c in payload.get("candidates", []) if c.get("candidate_id") is not None}
        actions=[]
        for item in value.get("actions", []):
            if not isinstance(item, dict): continue
            cid, act = str(item.get("candidate_id", "")), str(item.get("action", "review")).lower()
            if cid not in valid_ids or act not in _ALLOWED: continue
            try: conf=max(0.0,min(1.0,float(item.get("confidence",0))))
            except (TypeError,ValueError): conf=0.0
            actions.append({"candidate_id":cid,"action":act,"confidence":conf,"reason":str(item.get("reason",""))[:500]})
        return {"mode":"ai","observations":value.get("observations",[])[:20],"recommendations":value.get("recommendations",[])[:20],"actions":actions[:50],"message":"Validated advisory response"}
