from smartpc.network_recovery import build_plan


def test_dns_failure_plans_flush():
    plan = build_plan([{"code": "NET_DNS_FAILURE", "title": "DNS failed", "safe_actions": ["flush_dns"]}])
    assert [x.action for x in plan] == ["flush_dns"]
    assert plan[0].risk == "safe"


def test_gateway_failure_plans_only_evidence_backed_recovery():
    plan = build_plan([{"code": "NET_GATEWAY_UNREACHABLE", "title": "Gateway failed", "safe_actions": ["renew_dhcp"]}])
    assert [x.action for x in plan] == ["renew_dhcp"]
    assert plan[0].risk == "low"


def test_winsock_requires_explicit_evidence():
    plan = build_plan([{"code": "NET_STACK_SUSPECTED", "title": "Network stack issue", "safe_actions": ["reset_winsock"]}])
    assert [x.action for x in plan] == ["reset_winsock"]
    assert plan[0].risk == "medium"
    assert plan[0].requires_reboot is True


def test_proxy_is_not_auto_reset():
    plan = build_plan([{"code": "NET_WINHTTP_PROXY", "title": "Proxy configured", "safe_actions": ["review_proxy"]}])
    assert plan == []


def test_unknown_issue_produces_no_repair():
    assert build_plan([{"code": "NET_UNKNOWN", "title": "Unknown"}]) == []
