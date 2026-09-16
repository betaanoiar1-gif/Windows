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
    """Deterministic gate for unattended cleanup; quarantine is the only allowed mutation."""

    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy()

    def allow(self, candidate: Candidate, current_count: int, current_bytes: int) -> bool:
        if not self.policy.auto_safe_cleanup:
            return False
        if candidate.risk != self.policy.max_risk:
            return False
        if candidate.action is not Action.QUARANTINE:
            return False
        if not candidate.reversible:
            return False
        if current_count < 0 or current_bytes < 0:
            return False
        if current_count >= self.policy.max_auto_files:
            return False
        if candidate.size < 0 or current_bytes + candidate.size > self.policy.max_auto_bytes:
            return False
        return True
