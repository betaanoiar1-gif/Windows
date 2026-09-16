from pathlib import Path
import os
from .models import Candidate, Action, Risk


def _roots():
    names = ["WINDIR", "ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"]
    roots = []
    for n in names:
        value = os.environ.get(n)
        if value:
            roots.append(Path(value))
    return roots

PROTECTED_ROOTS = _roots()


def is_protected(path: str) -> bool:
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
