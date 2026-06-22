param(
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

# The script lives in scripts/, so the project root is one level up.
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$FrontendDir = Join-Path $RootDir "frontend"

function Write-SlcLog {
    param([string]$Message)
    Write-Host "[smart-labor-prod] $Message"
}

Write-SlcLog "Project root: $RootDir"
Write-SlcLog "Frontend dir: $FrontendDir"

# npm.cmd is the Windows entrypoint installed with Node.js.
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) {
    throw "[smart-labor-prod] ERROR: npm.cmd not found. Install Node.js first."
}

Push-Location $FrontendDir
try {
    # Install dependencies when requested or when node_modules is missing.
    if ($InstallDeps -or -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-SlcLog "Installing frontend dependencies..."
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) {
            throw "[smart-labor-prod] ERROR: npm install failed."
        }
    }

    # Build frontend/dist for production static hosting.
    Write-SlcLog "Building frontend dist..."
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) {
        throw "[smart-labor-prod] ERROR: frontend build failed."
    }
} finally {
    Pop-Location
}

Write-SlcLog "Frontend dist ready:"
Write-Host "  $(Join-Path $FrontendDir 'dist')"
