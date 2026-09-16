from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Risk(str, Enum):
    SAFE="safe"; LOW="low"; MEDIUM="medium"; HIGH="high"; CRITICAL="critical"

class Action(str, Enum):
    KEEP="keep"; REVIEW="review"; QUARANTINE="quarantine"; DELETE="delete"; DISABLE="disable"

@dataclass
class Candidate:
    target: str
    kind: str
    size: int = 0
    age_days: float = 0
    risk: Risk = Risk.SAFE
    action: Action = Action.KEEP
    reason: str = ""
    reversible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemSnapshot:
    timestamp: str
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    disk_free_gb: float
    process_count: int
    boot_seconds: float | None
    top_processes: list[dict[str, Any]]
