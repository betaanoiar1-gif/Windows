from smartpc.network import NetworkSnapshot, diagnose, recommended_repairs
from smartpc.network_health import evaluate, stability
from smartpc.network_recovery import build_plan


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


def test_gateway_failure_recommends_recovery():
    s = make_snapshot(gateway_ping={"ok": False}, dns={"ok": True})
    issues = diagnose(s)
    assert any(x["code"] == "NET_GATEWAY_UNREACHABLE" for x in issues)
    assert "renew_dhcp" in recommended_repairs(issues)
    assert "reset_winsock" in recommended_repairs(issues)


def test_no_interface_is_high_severity():
    s = make_snapshot()
    s.interfaces = []
    issues = diagnose(s)
    assert issues[0]["code"] == "NET_NO_ACTIVE_INTERFACE"
    assert issues[0]["severity"] == "high"


def test_health_degrades_with_gateway_loss():
    s = make_snapshot(gateway_ping={"ok": False, "packet_loss_percent": 100}, dns={"ok": True})
    h = evaluate(s)
    assert h.state == "poor"
    assert h.score < 60


def test_recovery_plan_orders_basic_repairs():
    s = make_snapshot(gateway_ping={"ok": False}, dns={"ok": True})
    plan = build_plan(diagnose(s))
    assert [x.action for x in plan] == ["renew_dhcp", "reset_winsock"]
    assert plan[0].risk == "low"
    assert plan[1].requires_reboot is False


def test_stability_summary():
    healthy = evaluate(make_snapshot(gateway_ping={"ok": True}, dns={"ok": True, "latency_ms": 20}))
    poor = evaluate(make_snapshot(gateway_ping={"ok": False}, dns={"ok": False}))
    result = stability([healthy, poor])
    assert result["samples"] == 2
    assert result["degraded_ratio"] == 0.5
