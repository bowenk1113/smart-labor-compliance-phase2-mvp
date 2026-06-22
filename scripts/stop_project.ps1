param()

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$RunDir = Join-Path $RootDir ".run"
$LogDir = Join-Path $RootDir "logs"

function Write-SlcLog {
    param([string]$Message)
    Write-Host "[smart-labor] $Message"
}

function Stop-FromPidFile {
    param([string]$Name, [string]$PidFile)
    if (-not (Test-Path $PidFile)) {
        Write-SlcLog "$Name has no PID file, skipped."
        return
    }
    $pidText = (Get-Content $PidFile -Raw).Trim()
    if (-not $pidText) {
        Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
        return
    }
    $pidValue = [int]$pidText
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($process) {
        Write-SlcLog "Stopping $Name, PID: $pidValue"
        Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    } else {
        Write-SlcLog "$Name PID is not alive: $pidValue"
    }
    Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
}

function Stop-ResidualProjectProcesses {
    param([string]$RootDir)
    $processes = Get-CimInstance Win32_Process | Where-Object {
        (
            $_.CommandLine -like "*uvicorn app.main:app*" -and
            $_.ExecutablePath -like "E:\anaconda\envs\RAG\*"
        ) -or (
            $_.CommandLine -like "*$RootDir*frontend*node_modules*vite*"
        )
    }
    foreach ($item in $processes) {
        Write-SlcLog "Stopping residual process $($item.Name), PID: $($item.ProcessId)"
        Stop-Process -Id $item.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
}
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

Stop-FromPidFile -Name "Frontend" -PidFile (Join-Path $RunDir "frontend.pid")
Stop-FromPidFile -Name "Backend API" -PidFile (Join-Path $RunDir "backend.pid")
Stop-ResidualProjectProcesses -RootDir $RootDir

Write-SlcLog "Stopped."
Write-Host "Logs: $LogDir"
