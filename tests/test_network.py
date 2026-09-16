from smartpc.network import NetworkSnapshot, diagnose, recommended_repairs


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
