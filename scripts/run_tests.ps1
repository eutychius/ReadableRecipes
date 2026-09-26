# Run the test suite with the workspace venv (./venv).
# Usage: .\scripts\run_tests.ps1

$ErrorActionPreference = "Stop"

# Resolve the project root from the script location.
$root = Split-Path -Parent $PSScriptRoot
$venvActivate = Join-Path $root "venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Error "venv not found. Create it first: python -m venv venv"
}

# Activate the venv in this session.
. $venvActivate

# Run pytest with the venv Python.
python -m pytest tests -q
exit $LASTEXITCODE
