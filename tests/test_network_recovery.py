from smartpc.network_recovery import build_plan


def test_dns_failure_plans_flush():
    plan = build_plan([{"code": "NET_DNS_FAILURE", "title": "DNS failed"}])
    assert [x.action for x in plan] == ["flush_dns"]
    assert plan[0].risk == "safe"


def test_gateway_failure_plans_recovery():
    plan = build_plan([{"code": "NET_GATEWAY_UNREACHABLE", "title": "Gateway failed"}])
    assert [x.action for x in plan] == ["renew_dhcp", "reset_winsock"]


def test_proxy_is_not_auto_reset():
    plan = build_plan([{"code": "NET_WINHTTP_PROXY", "title": "Proxy configured", "safe_actions": ["review_proxy"]}])
    assert plan == []
