# SMARTPC AI

Safety-first Windows optimization laboratory and desktop application.

## Runtime architecture

`OBSERVE → DIAGNOSE → PROPOSE → SAFETY CHECK → SIMULATE → EXECUTE → MEASURE → VERIFY → LEARN`

The platform is designed so AI can reason about evidence but cannot directly execute arbitrary system commands. Local deterministic policy and the safety engine remain authoritative.

## What it does

- Real CPU, RAM, disk, network and process telemetry through `psutil`.
- Read-only Windows startup inventory.
- Device-specific baselines and deterministic anomaly diagnostics.
- Temporary-file discovery with scan limits and reparse/symlink avoidance.
- Protected Windows/application roots.
- Reversible quarantine with an append-only JSONL manifest and restore command.
- SQLite history for measurements and actions.
- Optional provider-neutral OpenAI-compatible AI advisory layer.
- Schema-validated AI output; AI cannot authorize arbitrary commands, registry edits, service changes, process termination, or permanent deletion.
- Explicit Windows logon task controls; startup observation is read-only by default.
- Disposable test-lab fixture generator.
- Windows CI test gate.

## Network Intelligence & Self-Healing

The network subsystem is a first-class diagnostic and recovery layer, not a cosmetic "internet booster". It collects real Windows/OS measurements and separates LAN, DNS and internet symptoms.

### Observation

- active adapters, addresses, link state, reported speed and MTU;
- default gateway and gateway reachability;
- DNS servers and real DNS-resolution probes;
- WinHTTP proxy state;
- bounded Windows ping probes with packet-loss/latency extraction;
- network byte/packet counters;
- network health score and stability indicators.

### Diagnosis

The system distinguishes conditions such as no active interface, missing gateway, unreachable gateway, DNS failure and configured proxy. A configured proxy is treated as potentially intentional and is not automatically removed.

### Recovery planner

The planner selects the least-disruptive supported action for the observed evidence:

- `flush_dns` — safe cache refresh;
- `renew_dhcp` — refresh address/gateway configuration;
- `reset_winsock` — disruptive recovery for persistent connectivity problems;
- `reset_tcpip` — disruptive TCP/IP recovery when explicitly selected.

A recovery plan can be inspected without executing it:

```powershell
python main.py --network-plan
```

Explicit individual repairs:

```powershell
python main.py --network-repair flush_dns
python main.py --network-repair renew_dhcp
python main.py --network-repair reset_winsock
python main.py --network-repair reset_tcpip
```

Repairs return command results and post-repair evidence. Winsock/TCP-IP resets are treated as disruptive and may require a reboot. They are never part of silent startup optimization.

Inspect network health without changing anything:

```powershell
python main.py --network
```

Full system inspection also includes network evidence:

```powershell
python main.py --inspect
```

## Cloud-first test plan

Use a disposable Windows VM first (Azure is suitable). Clone this repository, install Python 3.12, then run the tests and read-only inspection. Keep the AI key out of Git and configure it only inside the disposable VM after the provider endpoint/model contract has been verified.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -q
python main.py --network
python main.py --network-plan
python main.py --inspect
```

The GUI is available with `python main.py`.

## Safe operations

`python main.py --optimize-safe` can move only locally-authorized temporary files into the application's quarantine directory. It does not permanently delete them. Restore with:

```powershell
python main.py --restore TOKEN
```

Install observation at logon only when explicitly requested:

```powershell
python main.py --install-startup
python main.py --startup-status
python main.py --remove-startup
```

## AI configuration

Copy `.env.example` to `.env` in the disposable test environment or use environment variables:

- `AI_API_KEY`
- `AI_BASE_URL`
- `AI_MODEL`

No AI key is required for telemetry, network diagnostics, scanning, quarantine, history, or tests.

## Safety contract

No optimization is considered successful without measurable before/after evidence. The default system does not modify the registry, disable services, terminate processes, change drivers, or permanently delete personal files. Network repairs are explicit user-invoked actions, not automatic startup actions. AI is advisory; local deterministic policy is authoritative.
