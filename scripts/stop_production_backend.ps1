param()

$ErrorActionPreference = "Stop"

# The script lives in scripts/, so the project root is one level up.
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$PidFile = Join-Path $RootDir ".run\prod_backend.pid"

function Write-SlcLog {
    param([string]$Message)
    Write-Host "[smart-labor-prod] $Message"
}

if (-not (Test-Path $PidFile)) {
    Write-SlcLog "Production backend has no PID file, skipped."
    exit 0
}

$pidText = (Get-Content $PidFile -Raw).Trim()
if (-not $pidText) {
    Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
    Write-SlcLog "Empty PID file removed."
    exit 0
}

$pidValue = [int]$pidText
$process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($process) {
    Write-SlcLog "Stopping production backend, PID: $pidValue"
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
} else {
    Write-SlcLog "Production backend PID is not alive: $pidValue"
}

# Uvicorn with --workers may leave multiprocessing children after the parent PID exits.
$residualProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.ParentProcessId -eq $pidValue -or
    ($_.CommandLine -like "*spawn_main(parent_pid=$pidValue,*")
}
foreach ($item in $residualProcesses) {
    Write-SlcLog "Stopping residual production backend, PID: $($item.ProcessId)"
    Stop-Process -Id $item.ProcessId -Force -ErrorAction SilentlyContinue
}

Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
Write-SlcLog "Stopped."
