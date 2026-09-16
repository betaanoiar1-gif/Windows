# SMARTPC AI

Safety-first Windows optimization laboratory and desktop application.

## What it does

The runtime follows:

`OBSERVE → DIAGNOSE → PROPOSE → SAFETY CHECK → QUARANTINE → MEASURE → LEARN`

- Real CPU, RAM, disk, network and process telemetry through `psutil`.
- Read-only startup inventory on Windows.
- Deterministic threshold/anomaly diagnostics against the device's own recent baseline.
- Temporary-file discovery with scan limits and reparse/symlink avoidance.
- Protected Windows/application roots.
- Reversible quarantine with an append-only JSONL manifest and restore command.
- SQLite history for measurements and actions.
- Optional provider-neutral OpenAI-compatible AI advisory layer.
- AI output is schema-validated and cannot authorize arbitrary commands, registry edits, service changes, process termination, or permanent deletion.
- Explicit Windows logon task controls; the task is observation-only by default.
- Disposable test-lab fixture generator.
- Windows CI test gate.

## Cloud-first test plan

Use a disposable Windows VM first (Azure is suitable). Clone this repository, install Python 3.12, then run the local tests and CLI inspection. Keep the AI key out of Git and configure it only inside the disposable VM after the provider's endpoint/model contract has been verified.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -q
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

No AI key is required for telemetry, diagnostics, scanning, quarantine, history, or tests.

## Safety contract

No optimization is considered successful without measurable before/after evidence. The default system does not modify the registry, disable services, terminate processes, change drivers, or permanently delete personal files. AI is advisory; local deterministic policy is authoritative.
