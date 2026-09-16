# SMARTPC AI

Safety-first Windows optimization laboratory and desktop application.

## Runtime architecture

`OBSERVE → DIAGNOSE → PROPOSE → SAFETY CHECK → SIMULATE → EXECUTE → MEASURE → VERIFY → LEARN`

AI is advisory only. Local deterministic policy and the safety engine remain authoritative over every system-changing operation.

## Current capabilities

- Real CPU, RAM, disk, process and network telemetry through `psutil`.
- Device-specific baseline and deterministic anomaly diagnostics.
- Read-only Windows startup inventory.
- Temporary-file discovery with bounded scans and reparse/symlink avoidance.
- Protected Windows/application roots.
- Reversible quarantine with restore support; no permanent deletion.
- SQLite history for snapshots and actions.
- Optional provider-neutral OpenAI-compatible AI advisory layer with strict candidate/action validation.
- Explicit Windows logon observation task controls.
- Disposable lab fixture generator.
- Unified Windows CI regression suite plus offline CLI smoke test.

## Network Intelligence & Recovery

The network subsystem diagnoses real connectivity layers rather than claiming to "boost" internet speed. It is designed to identify evidence-backed causes and recommend the least disruptive supported recovery.

### Read-only evidence

- active adapters, addresses, link state, reported speed and MTU;
- default gateway and bounded gateway ping;
- configured DNS servers and DNS-resolution latency;
- independent DNS and HTTPS reachability probes;
- multiple independent HTTPS GET probes;
- Wi-Fi state, SSID, signal, channel, radio type and link rates when Windows exposes them;
- WinHTTP proxy state, treated as potentially intentional;
- bounded IPv4 DF-ping MTU sampling/binary search;
- network byte/packet counters and health/stability indicators.

The gateway ping is an ICMP probe, not proof of Internet availability. When the gateway does not answer ICMP but external HTTPS succeeds, SMARTPC records the ICMP limitation as evidence instead of falsely declaring an Internet outage or recommending a repair. This follows Microsoft's guidance that ICMP can be blocked and should not be relied upon alone to prove overall connectivity. citeturn0search2turn0search1

Wi-Fi parsing accepts common English and French Windows labels and retains raw command output for evidence. MTU diagnostics never change the adapter MTU.

### Recovery

Supported explicit actions are:

- `flush_dns` — refresh DNS cache;
- `renew_dhcp` — refresh DHCP configuration;
- `reset_winsock` — disruptive Winsock reset;
- `reset_tcpip` — disruptive TCP/IP reset.

Recovery plans are generated from observed evidence. Medium-risk actions require explicit confirmation; administrator-required operations are blocked without elevation. Unsupported or tampered recovery actions are rejected. Every successful repair can be re-probed and compared with before/after health evidence.

Inspect without changes:

```powershell
python main.py --network
python main.py --network-plan
python main.py --inspect --no-ai
```

For deterministic/offline diagnostics and CI:

```powershell
python main.py --inspect --no-ai --no-network-probes
```

Explicit repairs:

```powershell
python main.py --network-repair flush_dns
python main.py --network-repair renew_dhcp
python main.py --network-repair reset_winsock --confirm
python main.py --network-repair reset_tcpip --confirm
```

A repair command never silently escalates privileges. If an operation needs administrator elevation, it is reported as skipped unless the process is already elevated.

## Safe optimization

```powershell
python main.py --optimize-safe
python main.py --restore TOKEN
```

Safe optimization moves only locally-authorized temporary files to quarantine. It never permanently deletes them.

## Startup observation

Startup observation is not enabled automatically. Install it only by explicit request:

```powershell
python main.py --install-startup
python main.py --startup-status
python main.py --remove-startup
```

The installed task invokes `--background`, which performs observation only and disables AI/network probes.

## AI configuration

Set these environment variables only in the disposable test environment:

- `AI_API_KEY`
- `AI_BASE_URL`
- `AI_MODEL`

No AI key is required for telemetry, network diagnostics, scanning, quarantine, history or tests. When AI is enabled, the supplied system/candidate evidence is sent to the configured provider; the provider never receives authority to execute commands.

## Test gate

The GitHub Actions Windows job performs:

1. dependency installation;
2. Python compilation of the full application;
3. the complete pytest regression suite;
4. CLI help smoke test;
5. offline system inspection smoke test with AI and external network probes disabled.

The separate Windows lab validates the application on a real hosted Windows VM, including network intelligence, startup read-only inspection and safe-optimization dry validation.

For a real machine, use a disposable Windows VM first. The repository includes `lab/bootstrap.ps1` for repeatable setup. Passing CI does not mean the application has been exercised on your personal PC.

## Safety contract

No optimization is considered successful without measurable evidence. The default system does not modify the registry, disable services, terminate processes, change drivers, or permanently delete personal files. Network repairs are explicit user-invoked operations, not automatic startup actions. AI cannot authorize arbitrary commands or bypass local safety controls.
