from smartpc.network import NetworkSnapshot, diagnose, recommended_repairs
from smartpc.network_diagnostics import diagnose_connectivity
from smartpc.network_health import evaluate, stability
from smartpc.network_recovery import build_plan, execute_verified


def make_snapshot(**internet):
    return NetworkSnapshot(
        timestamp=0.0,
        interfaces=[{"name": "Ethernet", "addresses": [{"address": "192.168.1.10", "netmask": "255.255.255.0"}], "is_up": True, "speed_mbps": 1000, "mtu": 1500}],
        default_gateways=["192.168.1.1"],
        dns_servers=["192.168.1.1"],
        proxy={"enabled": False},
        internet=internet,
        counters={"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0},
    )


def test_dns_failure_has_safe_first_repair():
    s = make_snapshot(gateway_ping={"ok": True}, dns={"ok": False})
    issues = diagnose(s)
    assert any(x["code"] == "NET_DNS_FAILURE" for x in issues)
    assert recommended_repairs(issues) == ["flush_dns"]


def test_gateway_failure_recommends_only_low_impact_recovery():
    s = make_snapshot(gateway_ping={"ok": False}, dns={"ok": True})
    issues = diagnose(s)
    assert any(x["code"] == "NET_GATEWAY_UNREACHABLE" for x in issues)
    assert recommended_repairs(issues) == ["renew_dhcp"]


def test_gateway_icmp_failure_is_not_outage_when_https_works():
    s = make_snapshot(gateway_ping={"ok": False, "packet_loss_percent": 100}, dns={"ok": True})
    connectivity = diagnose_connectivity({"ok": True}, {"ok": True})
    issues = diagnose(s, connectivity=connectivity)
    assert [x["code"] for x in issues] == ["NET_GATEWAY_ICMP_BLOCKED"]
    assert recommended_repairs(issues) == []
    health = evaluate(s, connectivity=connectivity)
    assert health.score == 100
    assert health.state == "healthy"


def test_no_interface_is_high_severity():
    s = make_snapshot()
    s.interfaces = []
    issues = diagnose(s)
    assert issues[0]["code"] == "NET_NO_ACTIVE_INTERFACE"
    assert issues[0]["severity"] == "high"


def test_health_degrades_with_gateway_loss_without_layered_evidence():
    s = make_snapshot(gateway_ping={"ok": False, "packet_loss_percent": 100}, dns={"ok": True})
    h = evaluate(s)
    assert h.state == "poor"
    assert h.score < 60


def test_recovery_plan_orders_basic_repairs():
    s = make_snapshot(gateway_ping={"ok": False}, dns={"ok": True})
    plan = build_plan(diagnose(s))
    assert [x.action for x in plan] == ["renew_dhcp"]
    assert plan[0].risk == "low"


def test_medium_risk_repair_requires_explicit_confirmation():
    from smartpc.network_recovery import RecoveryStep
    result = execute_verified([RecoveryStep("reset_winsock", "test", "medium")])
    assert result[0]["skipped"] is True


def test_layered_connectivity_classification():
    assert diagnose_connectivity({"ok": False, "error": "dns"}, {"ok": False, "error": "dns"}).state == "unreachable"
    assert diagnose_connectivity({"ok": True}, {"ok": False, "error": "blocked"}).state == "dns_only"
    assert diagnose_connectivity({"ok": True}, {"ok": True}).state == "internet_reachable"


def test_stability_summary():
    healthy = evaluate(make_snapshot(gateway_ping={"ok": True}, dns={"ok": True, "latency_ms": 20}))
    poor = evaluate(make_snapshot(gateway_ping={"ok": False}, dns={"ok": False}))
    result = stability([healthy, poor])
    assert result["samples"] == 2
    assert result["degraded_ratio"] == 0.5
