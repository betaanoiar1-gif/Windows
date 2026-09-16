from smartpc.models import Action, Candidate, Risk
from smartpc.policy import Policy, PolicyEngine


def test_policy_disabled_by_default():
    c = Candidate("C:/Temp/x.tmp", "temporary", 10, 5, risk=Risk.SAFE, action=Action.QUARANTINE, reversible=True)
    assert not PolicyEngine().allow(c, 0, 0)


def test_policy_bounds_safe_cleanup():
    policy = Policy(auto_safe_cleanup=True, max_auto_files=1, max_auto_bytes=100)
    engine = PolicyEngine(policy)
    c = Candidate("C:/Temp/x.tmp", "temporary", 10, 5, risk=Risk.SAFE, action=Action.QUARANTINE, reversible=True)
    assert engine.allow(c, 0, 0)
    assert not engine.allow(c, 1, 10)
