# SMARTPC AI

Autonomous Windows optimization laboratory. The project is deliberately safety-first: AI never receives direct shell/system authority, destructive operations are blocked by a local safety layer, and cleanup uses quarantine rather than irreversible deletion.

## Current architecture

- Real CPU/RAM/disk/process telemetry via `psutil`.
- Temporary-file discovery.
- Protected Windows/application paths.
- Dry inspection with no changes.
- Reversible quarantine for automatic cleanup.
- SQLite history of snapshots/actions.
- Provider-neutral OpenAI-compatible AI adapter (disabled until configured).
- PySide6 desktop UI.
- Windows GitHub Actions test gate.

## Run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Safety

The first test phase must use a disposable Windows VM. Do not put an API key in source control. Copy `.env.example` to `.env` only in the test environment or use environment variables/secrets.

The current cleanup mode moves approved temporary files into the local `quarantine/` directory. It does not permanently delete them.

## AI configuration

AI is intentionally off until the cloud laboratory phase. Set `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL` only after the exact provider contract is verified. AI output is advisory and must pass local safety validation before any action.

## Development rule

No optimization is considered successful without a measurable before/after result. No registry tweak, service disablement, process termination, or personal-file deletion is enabled by default.
