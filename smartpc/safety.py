from pathlib import Path
import os
from .models import Candidate, Action, Risk


def _roots():
    names = ["WINDIR", "ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"]
    return [Path(os.environ[n]) for n in names if os.environ.get(n)]

PROTECTED_ROOTS = _roots()
_WINDOWS_PROTECTED = (r"c:\windows", r"c:\program files", r"c:\program files (x86)")


def is_protected(path: str) -> bool:
    raw = str(path).replace("/", "\\").lower().rstrip("\\")
    if any(raw == x or raw.startswith(x + "\\") for x in _WINDOWS_PROTECTED):
        return True
    try:
        p = Path(path).resolve()
        for root in PROTECTED_ROOTS:
            r = root.resolve()
            if p == r or r in p.parents:
                return True
        return False
    except (OSError, RuntimeError, ValueError):
        return True


def authorize(c: Candidate, auto: bool = False) -> Candidate:
    if is_protected(c.target):
        c.risk, c.action, c.reversible = Risk.CRITICAL, Action.KEEP, False
        c.reason = "Protected operating-system/application path"
        return c
    if c.kind == "temporary":
        c.risk = Risk.SAFE
        c.action = Action.QUARANTINE if auto and c.reversible else Action.REVIEW
        c.reason = "Temporary data; reversible quarantine is the only automatic cleanup operation"
    elif c.action in (Action.DELETE, Action.DISABLE):
        c.risk = Risk.HIGH
        c.action = Action.REVIEW
        c.reason = "Destructive/system-changing operation requires explicit review"
    return c


def authorize_all(items, auto: bool = False):
    return [authorize(x, auto) for x in items]
