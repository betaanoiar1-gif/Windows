from pathlib import Path
import os
from .models import Candidate, Action, Risk

PROTECTED_ROOTS=[Path(os.environ.get("WINDIR",r"C:\Windows")),Path(os.environ.get("ProgramFiles",r"C:\Program Files")),Path(os.environ.get("ProgramW6432",r"C:\Program Files")),Path(os.environ.get("ProgramFiles(x86)",r"C:\Program Files (x86)"))]

def is_protected(path: str)->bool:
    try:
        p=Path(path).resolve()
        return any(p==r.resolve() or r.resolve() in p.parents for r in PROTECTED_ROOTS if r.exists())
    except OSError:return True

def authorize(c: Candidate, auto=False)->Candidate:
    if is_protected(c.target):
        c.risk=Risk.CRITICAL; c.action=Action.KEEP; c.reason="Protected Windows/application path"; c.reversible=False; return c
    if c.kind=="temporary" and c.size>=0:
        c.risk=Risk.SAFE; c.action=Action.QUARANTINE if auto else Action.REVIEW
        c.reason="Temporary data; reversible quarantine preferred"
    return c

def authorize_all(items, auto=False): return [authorize(x,auto) for x in items]
