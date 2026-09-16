from __future__ import annotations

from dataclasses import dataclass

from .models import Action, Candidate, Risk


@dataclass(frozen=True)
class Policy:
    auto_safe_cleanup: bool = False
    max_auto_files: int = 50
    max_auto_bytes: int = 512 * 1024 * 1024
    max_risk: Risk = Risk.SAFE


class PolicyEngine:
    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy()

    def allow(self, candidate: Candidate, current_count: int, current_bytes: int) -> bool:
        if not self.policy.auto_safe_cleanup:
            return False
        if candidate.risk != self.policy.max_risk:
            return False
        if candidate.action not in {Action.QUARANTINE, Action.DELETE}:
            return False
        if current_count >= self.policy.max_auto_files:
            return False
        if current_bytes + candidate.size > self.policy.max_auto_bytes:
            return False
        return bool(candidate.reversible)
