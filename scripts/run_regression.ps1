# wxauto4 regression test runner (PowerShell)
# Usage: .\scripts\run_regression.ps1 [-Online]

param(
    [switch]$Online
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "wxauto4 Regression Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location "$PSScriptRoot\.."

Write-Host "`n[1/3] Safety Check..." -ForegroundColor Yellow
python tests\safety_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "SAFETY CHECK FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/3] Offline Regression..." -ForegroundColor Yellow
python tests\regression_all.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "REGRESSION FAILED" -ForegroundColor Red
    exit 1
}

if ($Online) {
    Write-Host "`n[3/3] Online Regression..." -ForegroundColor Yellow
    python tests\regression_all.py --online
} else {
    Write-Host "`n[3/3] Skipping online tests (use -Online to include)" -ForegroundColor Gray
}

Write-Host "`nALL TESTS PASSED" -ForegroundColor Green
