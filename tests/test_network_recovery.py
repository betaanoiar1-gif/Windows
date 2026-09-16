from smartpc.network_recovery import RecoveryStep, build_plan, execute_verified


def test_dns_failure_plans_flush():
    plan = build_plan([{"code": "NET_DNS_FAILURE", "title": "DNS failed", "safe_actions": ["flush_dns"]}])
    assert [x.action for x in plan] == ["flush_dns"]
    assert plan[0].risk == "safe"
    assert plan[0].requires_admin is False


def test_gateway_failure_plans_only_evidence_backed_recovery():
    plan = build_plan([{"code": "NET_GATEWAY_UNREACHABLE", "title": "Gateway failed", "safe_actions": ["renew_dhcp"]}])
    assert [x.action for x in plan] == ["renew_dhcp"]
    assert plan[0].risk == "low"
    assert plan[0].requires_admin is True


def test_winsock_requires_explicit_evidence():
    plan = build_plan([{"code": "NET_STACK_SUSPECTED", "title": "Network stack issue", "safe_actions": ["reset_winsock"]}])
    assert [x.action for x in plan] == ["reset_winsock"]
    assert plan[0].risk == "medium"
    assert plan[0].requires_reboot is True
    assert plan[0].requires_admin is True


def test_proxy_is_not_auto_reset():
    plan = build_plan([{"code": "NET_WINHTTP_PROXY", "title": "Proxy configured", "safe_actions": ["review_proxy"]}])
    assert plan == []


def test_unknown_issue_produces_no_repair():
    assert build_plan([{"code": "NET_UNKNOWN", "title": "Unknown"}]) == []


def test_medium_risk_requires_confirmation_before_admin_check():
    result = execute_verified(
        [RecoveryStep("reset_winsock", "test", "medium", requires_admin=True)],
        admin_check=lambda: True,
    )
    assert result[0]["skipped"] is True
    assert "confirmation" in result[0]["reason"]


def test_admin_required_actions_are_skipped_without_elevation():
    result = execute_verified(
        [RecoveryStep("renew_dhcp", "test", "low", requires_admin=True)],
        admin_check=lambda: False,
    )
    assert result[0]["skipped"] is True
    assert result[0]["reason"] == "administrator elevation required"


def test_confirmed_admin_action_can_reach_repair(monkeypatch):
    calls = []

    def fake_repair(action):
        calls.append(action)
        return {"action": action, "ok": True}

    monkeypatch.setattr("smartpc.network_recovery.repair", fake_repair)
    result = execute_verified(
        [RecoveryStep("renew_dhcp", "test", "low", requires_admin=True)],
        confirm=lambda step: True,
        admin_check=lambda: True,
    )
    assert result == [{"action": "renew_dhcp", "ok": True}]
    assert calls == ["renew_dhcp"]


def test_unsupported_or_tampered_step_is_rejected(monkeypatch):
    called = []
    monkeypatch.setattr("smartpc.network_recovery.repair", lambda action: called.append(action) or {"action": action, "ok": True})
    result = execute_verified([RecoveryStep("not-a-real-action", "test", "safe")], confirm=lambda _: True, admin_check=lambda: True)
    assert result[0]["skipped"] is True
    assert called == []

    result = execute_verified([RecoveryStep("reset_winsock", "test", "safe")], confirm=lambda _: True, admin_check=lambda: True)
    assert result[0]["skipped"] is True
    assert called == []
