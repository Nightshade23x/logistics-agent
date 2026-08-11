param(
    [string]$Repo = $PSScriptRoot,
    [string]$Python = "G:\venvs\logistics-training\Scripts\python.exe",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
    [switch]$StopOnly
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Stop-PortListener {
    param([int]$Port)

    $connections = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue

    if (-not $connections) {
        Write-Host "Port $Port is already free."
        return
    }

    $processIds = $connections |
        Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($processId in $processIds) {
        try {
            $process = Get-Process -Id $processId -ErrorAction Stop
            Write-Host (
                "Stopping PID {0} ({1}) on port {2}..." -f
                $processId,
                $process.ProcessName,
                $Port
            ) -ForegroundColor Yellow

            Stop-Process -Id $processId -Force -ErrorAction Stop
        }
        catch {
            Write-Warning (
                "Could not stop PID {0} on port {1}: {2}" -f
                $processId,
                $Port,
                $_.Exception.Message
            )
        }
    }
}

function Wait-ForUrl {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 3 |
                Out-Null

            Write-Host "PASS - $Name is responding at $Url" -ForegroundColor Green
            return $true
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    Write-Host (
        "FAIL - {0} did not respond within {1} seconds. Check its terminal." -f
        $Name,
        $TimeoutSeconds
    ) -ForegroundColor Red

    return $false
}

Write-Host "LOGISTICS APP LAUNCHER" -ForegroundColor White
Write-Host "======================" -ForegroundColor White

if (-not (Test-Path -LiteralPath $Repo -PathType Container)) {
    throw "Repository not found: $Repo"
}

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python executable not found: $Python"
}

$frontendDirectory = Join-Path $Repo "frontend"
$packageJson = Join-Path $frontendDirectory "package.json"

if (-not (Test-Path -LiteralPath $packageJson -PathType Leaf)) {
    throw "Frontend package.json not found: $packageJson"
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue

if ($npmCommand) {
    $npm = $npmCommand.Source
}
elseif (Test-Path -LiteralPath "G:\npm.cmd" -PathType Leaf) {
    $npm = "G:\npm.cmd"
}
else {
    throw "npm.cmd could not be found in PATH or at G:\npm.cmd"
}

Write-Step "Repository check"
Write-Host "Repo:     $Repo"
Write-Host "Python:   $Python"
Write-Host "npm:      $npm"

try {
    $branch = (
        git -C $Repo branch --show-current 2>$null
    ).Trim()

    if ($branch) {
        Write-Host "Branch:   $branch"
    }

    $status = git -C $Repo status --short 2>$null

    if ($status) {
        Write-Host "Working tree has local changes:" -ForegroundColor Yellow
        $status | ForEach-Object {
            Write-Host "  $_"
        }
    }
    else {
        Write-Host "Working tree: clean" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Git status could not be read."
}

Write-Step "Stopping stale app processes"
Stop-PortListener -Port $BackendPort
Stop-PortListener -Port $FrontendPort

Start-Sleep -Seconds 2

if ($StopOnly) {
    Write-Host "`nBackend and frontend listeners have been stopped." -ForegroundColor Green
    exit 0
}

$escapedRepo = $Repo.Replace("'", "''")
$escapedPython = $Python.Replace("'", "''")
$escapedFrontend = $frontendDirectory.Replace("'", "''")
$escapedNpm = $npm.Replace("'", "''")

$backendCommand = @"
`$Host.UI.RawUI.WindowTitle = 'Logistics Backend :$BackendPort'
Set-Location -LiteralPath '$escapedRepo'
`$env:PYTHONPATH = '$escapedRepo'
Write-Host 'Starting Logistics backend...' -ForegroundColor Cyan
& '$escapedPython' -m uvicorn api_server:app --host 127.0.0.1 --port $BackendPort
Write-Host ''
Write-Host 'Backend stopped. Press Enter to close.' -ForegroundColor Yellow
Read-Host
"@

$frontendCommand = @"
`$Host.UI.RawUI.WindowTitle = 'Logistics Frontend :$FrontendPort'
Set-Location -LiteralPath '$escapedFrontend'
Write-Host 'Starting Logistics frontend...' -ForegroundColor Cyan
& '$escapedNpm' run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort
Write-Host ''
Write-Host 'Frontend stopped. Press Enter to close.' -ForegroundColor Yellow
Read-Host
"@

Write-Step "Starting backend"
Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $backendCommand
    ) |
    Out-Null

Start-Sleep -Seconds 3

Write-Step "Starting frontend"
Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $frontendCommand
    ) |
    Out-Null

Write-Step "Health checks"

$backendReady = Wait-ForUrl `
    -Name "Backend" `
    -Url "http://127.0.0.1:$BackendPort/docs" `
    -TimeoutSeconds 60

$frontendReady = Wait-ForUrl `
    -Name "Frontend" `
    -Url "http://127.0.0.1:$FrontendPort" `
    -TimeoutSeconds 60

if ($backendReady -and $frontendReady) {
    Write-Host "`nLogistics app is ready." -ForegroundColor Green

    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:$FrontendPort"
    }
}
else {
    Write-Host (
        "`nAt least one service failed its health check. " +
        "Read the backend and frontend terminal output."
    ) -ForegroundColor Red

    exit 1
}


