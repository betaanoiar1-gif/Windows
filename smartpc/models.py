from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

class Risk(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Action(str, Enum):
    KEEP = "keep"
    REVIEW = "review"
    QUARANTINE = "quarantine"
    DELETE = "delete"
    DISABLE = "disable"

@dataclass
class Candidate:
    target: str
    kind: str
    size: int = 0
    age_days: float = 0.0
    risk: Risk = Risk.SAFE
    action: Action = Action.KEEP
    reason: str = ""
    reversible: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["action"] = self.action.value
        return d

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
    load_1m: float | None = None
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Diagnosis:
    code: str
    severity: Risk
    title: str
    evidence: list[str] = field(default_factory=list)
    possible_causes: list[str] = field(default_factory=list)
    safe_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d

@dataclass
class ProposedAction:
    candidate_id: str
    action: Action
    reason: str
    confidence: float = 0.0
    expected_effect: str = ""
    risk: Risk = Risk.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        d["risk"] = self.risk.value
        return d
