param(
    [string]$BackendHost = "0.0.0.0",
    [int]$BackendPort = 8000,
    [int]$Workers = 2,
    [string]$VectorBackend = "",
    [switch]$NoServeFrontend,
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

# The script lives in scripts/, so the project root is one level up.
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RootDir "backend"
$RunDir = Join-Path $RootDir ".run"
$LogDir = Join-Path $RootDir "logs"
$PidFile = Join-Path $RunDir "prod_backend.pid"
$BackendLog = Join-Path $LogDir "prod_backend.log"
$BackendErrLog = Join-Path $LogDir "prod_backend.err.log"

function Write-SlcLog {
    param([string]$Message)
    Write-Host "[smart-labor-prod] $Message"
}

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Get-ProjectPython {
    # PYTHON_BIN has the highest priority when the server operator sets it.
    if ($env:PYTHON_BIN -and (Test-Path $env:PYTHON_BIN)) {
        return $env:PYTHON_BIN
    }

    # Prefer the dedicated SLC_2 environment when it exists.
    $slcPython = "E:\anaconda\envs\SLC_2\python.exe"
    if (Test-Path $slcPython) {
        return $slcPython
    }

    # The project default is the conda RAG environment.
    $ragPython = "E:\anaconda\envs\RAG\python.exe"
    if (Test-Path $ragPython) {
        return $ragPython
    }

    # Fall back to system Python.
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    throw "[smart-labor-prod] ERROR: Python not found. Set PYTHON_BIN or install/use the RAG conda env."
}

function Load-DotEnv {
    param([string]$EnvFile)
    if (-not (Test-Path $EnvFile)) {
        return
    }

    # Load backend/.env into the current PowerShell process.
    # The uvicorn child process will inherit these variables.
    foreach ($rawLine in Get-Content -Path $EnvFile -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $pair = $line.Split("=", 2)
        $key = $pair[0].Trim()
        $value = $pair[1].Trim().Trim('"').Trim("'")
        if ($key -and -not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Test-HttpReady {
    param([string]$Url)
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-HttpReady {
    param([string]$Url, [int]$Seconds = 80)
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-HttpReady $Url) {
            Write-SlcLog "Backend ready: $Url"
            return
        }
        Start-Sleep -Seconds 1
    }

    if (Test-Path $BackendLog) {
        Get-Content $BackendLog -Tail 40
    }
    if (Test-Path $BackendErrLog) {
        Get-Content $BackendErrLog -Tail 40
    }
    throw "[smart-labor-prod] ERROR: backend was not ready within ${Seconds}s."
}

function Stop-OldProductionBackend {
    if (-not (Test-Path $PidFile)) {
        return
    }

    $pidText = (Get-Content $PidFile -Raw).Trim()
    if ($pidText) {
        $oldProcess = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
        if ($oldProcess) {
            Write-SlcLog "Stopping old production backend, PID: $pidText"
            Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item -Force $PidFile -ErrorAction SilentlyContinue
}

Ensure-Dir $RunDir
Ensure-Dir $LogDir

$PythonBin = Get-ProjectPython
Write-SlcLog "Project root: $RootDir"
Write-SlcLog "Python: $PythonBin"

# Load backend/.env before starting uvicorn.
Load-DotEnv -EnvFile (Join-Path $BackendDir ".env")

# CLI VectorBackend overrides .env. If neither is set, production defaults to milvus.
if ($VectorBackend) {
    $env:PHASE2_VECTOR_BACKEND = $VectorBackend
} elseif (-not $env:PHASE2_VECTOR_BACKEND) {
    $env:PHASE2_VECTOR_BACKEND = "milvus"
}

if ($env:PHASE2_VECTOR_BACKEND -eq "milvus") {
    if (-not $env:MILVUS_URI) {
        $env:MILVUS_URI = "http://127.0.0.1:19531"
    }
    if (-not $env:PHASE2_FAQ_COLLECTION) {
        $env:PHASE2_FAQ_COLLECTION = "slc_phase2_faq_vectors_dedicated"
    }
    if (-not $env:PHASE2_DOC_COLLECTION) {
        $env:PHASE2_DOC_COLLECTION = "slc_phase2_doc_vectors_dedicated"
    }
}

# For this phase-2 MVP, production startup seeds demo tenant/admin data by default.
# The seed logic is idempotent, so repeated startup only fills missing demo data
# instead of creating unbounded duplicate records.
if (-not $env:AUTO_SEED) {
    $env:AUTO_SEED = "true"
}

# Without Nginx, FastAPI can serve frontend/dist directly.
if ($NoServeFrontend) {
    $env:SERVE_FRONTEND = "false"
} elseif (-not $env:SERVE_FRONTEND) {
    $env:SERVE_FRONTEND = "true"
}

if ($InstallDeps) {
    Write-SlcLog "Installing backend production dependencies..."
    & $PythonBin -m pip install --no-user -r (Join-Path $BackendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "[smart-labor-prod] ERROR: backend dependency installation failed."
    }
}

Stop-OldProductionBackend

# If the target port is still occupied, fail early with the owning PID.
$portListeners = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue | Where-Object {
    $_.LocalAddress -eq "0.0.0.0" -or $_.LocalAddress -eq "127.0.0.1"
}
if ($portListeners) {
    $owners = ($portListeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ","
    throw "[smart-labor-prod] ERROR: port $BackendPort is already in use. OwningProcess=$owners"
}

# Some antivirus or old worker process may keep the old log file open briefly.
# Use timestamped logs for the new run instead of failing on a locked file.
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (Test-Path $BackendLog) {
    try {
        Clear-Content -Path $BackendLog -ErrorAction Stop
    } catch {
        $BackendLog = Join-Path $LogDir "prod_backend_$runStamp.log"
    }
}
if (Test-Path $BackendErrLog) {
    try {
        Clear-Content -Path $BackendErrLog -ErrorAction Stop
    } catch {
        $BackendErrLog = Join-Path $LogDir "prod_backend_$runStamp.err.log"
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $BackendLog -Value "== $timestamp start production backend on ${BackendHost}:${BackendPort}, workers=${Workers}, vector=$env:PHASE2_VECTOR_BACKEND =="

# Production mode does not use --reload.
$args = "-m uvicorn app.main:app --host $BackendHost --port $BackendPort --workers $Workers"
Write-SlcLog "Starting production backend..."
$process = Start-Process `
    -FilePath $PythonBin `
    -ArgumentList $args `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -Path $PidFile -Value $process.Id
Wait-HttpReady -Url "http://127.0.0.1:$BackendPort/health"

Write-SlcLog "Started."
Write-Host "Backend: http://127.0.0.1:$BackendPort"
Write-Host "API docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Logs:    $LogDir"
