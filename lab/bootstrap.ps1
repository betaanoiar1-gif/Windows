$ErrorActionPreference = 'Stop'
Write-Host 'SMARTPC AI disposable Windows lab bootstrap'
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher (py) is required.' }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
Write-Host 'Lab bootstrap complete. Next: .\.venv\Scripts\python.exe main.py --inspect'
