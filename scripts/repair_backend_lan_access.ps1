param(
    [int]$OldPid = 0,
    [int]$BackendPort = 8001,
    [string]$BackendHost = "0.0.0.0",
    [int]$Workers = 1
)

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$StartScript = Join-Path $RootDir "scripts\start_production_backend.ps1"
$RuleName = "smart-labor-backend-$BackendPort"

if ($OldPid -gt 0) {
    Stop-Process -Id $OldPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

$existingRule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Set-NetFirewallRule -DisplayName $RuleName -Enabled True -Direction Inbound -Action Allow | Out-Null
} else {
    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $BackendPort | Out-Null
}

& $StartScript -BackendHost $BackendHost -BackendPort $BackendPort -Workers $Workers
