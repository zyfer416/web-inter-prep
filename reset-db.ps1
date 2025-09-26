param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = 'Stop'

Write-Host "Resetting local SQLite DB (development)" -ForegroundColor Cyan

Push-Location $PSScriptRoot

try {
    # Navigate to backend and run the reset script with the same Python used for dev
    Set-Location -Path "$PSScriptRoot/backend"
    if ($VerboseOutput) { Write-Host "Running: python scripts/reset_db.py" -ForegroundColor DarkGray }
    python scripts/reset_db.py
    Write-Host "DB reset complete." -ForegroundColor Green
}
catch {
    Write-Error "Reset failed: $_"
    exit 1
}
finally {
    Pop-Location
}


