<#
Starts the full orchestrator stack: Finance REST API in the background,
then the Orchestrator's own REST API in the foreground.
Risk/Compliance/Trader don't need to be pre-started -- the orchestrator
spawns them per-request via MCP stdio.
Run from the outer orchestrator_agent folder.
#>

$ErrorActionPreference = "Stop"

$financeDir = "$PSScriptRoot\..\..\..\agent-finance"
$orchestratorDir = "$PSScriptRoot\.."

Write-Host "Starting Finance Agent on port 8003..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$financeDir'; .venv\Scripts\python.exe -m uvicorn finance_agent.finance_agent.api:app --port 8003"
)

Write-Host "Waiting for Finance Agent to become healthy..." -ForegroundColor Cyan
$financeReady = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8003/docs" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $financeReady = $true
        break
    } catch {
        continue
    }
}

if (-not $financeReady) {
    Write-Host "Finance Agent did not become healthy in time. Check its window for errors." -ForegroundColor Red
    exit 1
}

Write-Host "Finance Agent is up." -ForegroundColor Green
Write-Host "Starting Orchestrator Agent on port 8010..." -ForegroundColor Cyan

cd $orchestratorDir
.venv\Scripts\python.exe -m uvicorn orchestrator_agent.api:app --port 8010