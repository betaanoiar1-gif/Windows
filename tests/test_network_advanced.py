from smartpc.network_advanced import ProbeResult, summarize_https


def test_https_summary_detects_partial_connectivity():
    result = summarize_https([
        ProbeResult("a", True, 20.0, 200),
        ProbeResult("b", False, 3000.0, error="timeout"),
    ])
    assert result["reachable"] is True
    assert result["successful"] == 1
    assert result["failed"] == 1
    assert result["consistent_failure"] is False


def test_https_summary_detects_total_failure():
    result = summarize_https([ProbeResult("a", False, 3000.0), ProbeResult("b", False, 3000.0)])
    assert result["reachable"] is False
    assert result["consistent_failure"] is True
