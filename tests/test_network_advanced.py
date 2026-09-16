from smartpc.network_advanced import ProbeResult, parse_wifi_interfaces, summarize_https, mtu_probe


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


def test_wifi_parser_extracts_numeric_evidence_from_english_output():
    text = """
    State                   : connected
    SSID                    : TestWiFi
    Signal                  : 87%
    Channel                 : 36
    Radio type              : 802.11ax
    Receive rate (Mbps)     : 1201.0
    Transmit rate (Mbps)    : 1201.0
    """
    parsed = parse_wifi_interfaces(text)
    assert len(parsed) == 1
    assert parsed[0]["ssid"] == "TestWiFi"
    assert parsed[0]["signal_percent"] == 87.0
    assert parsed[0]["channel"] == 36
    assert parsed[0]["receive_rate_mbps"] == 1201.0


def test_wifi_parser_handles_french_labels():
    text = """
    État                   : connecté
    SSID                    : Maison
    Signal du réseau       : 73%
    Canal                  : 11
    Type de radio          : 802.11n
    Vitesse de réception (Mbits/s) : 144.4
    Vitesse de transmission (Mbits/s) : 144.4
    """
    parsed = parse_wifi_interfaces(text)
    assert len(parsed) == 1
    assert parsed[0]["signal_percent"] == 73.0
    assert parsed[0]["channel"] == 11
    assert parsed[0]["transmit_rate_mbps"] == 144.4


def test_mtu_binary_search_is_bounded_and_reports_estimate():
    calls = []

    def runner(args, timeout):
        calls.append((args, timeout))
        size = int(args[args.index("-l") + 1])
        return (0, "", "") if size <= 1400 else (1, "", "too large")

    result = mtu_probe("192.0.2.1", runner=runner)
    assert result["largest_successful_payload"] == 1400
    assert result["mtu_estimate"] == 1428
    assert len(calls) <= 12
    assert all("-f" in args for args, _ in calls)


def test_mtu_sample_mode_clamps_and_deduplicates_sizes():
    calls = []

    def runner(args, timeout):
        calls.append(int(args[args.index("-l") + 1]))
        return 0, "", ""

    result = mtu_probe("192.0.2.1", payload_sizes=(2000, 1472, 1472, 100, 576), runner=runner)
    assert calls == [1472, 576]
    assert result["largest_successful_payload"] == 1472
    assert result["mtu_estimate"] == 1500
