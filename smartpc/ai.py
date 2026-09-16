import os, json, urllib.request

class AIClient:
    """OpenAI-compatible adapter. No key is required for local mode."""
    def __init__(self, base_url=None, model=None):
        self.base_url=(base_url or os.getenv("AI_BASE_URL","")).rstrip("/")
        self.model=model or os.getenv("AI_MODEL","")
        self.key=os.getenv("AI_API_KEY","")
    @property
    def enabled(self): return bool(self.base_url and self.model and self.key)
    def analyze(self, payload):
        if not self.enabled: return {"mode":"local","actions":[],"message":"AI API not configured"}
        body=json.dumps({"model":self.model,"messages":[{"role":"system","content":"Analyze Windows optimization telemetry. Never request destructive actions. Return JSON with observations, recommendations, confidence."},{"role":"user","content":json.dumps(payload)}],"temperature":0.1}).encode()
        req=urllib.request.Request(self.base_url+"/chat/completions",body,{"Content-Type":"application/json","Authorization":"Bearer "+self.key})
        with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read())
