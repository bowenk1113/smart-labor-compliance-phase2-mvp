param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$BackendHost = "0.0.0.0",
    [string]$FrontendHost = "0.0.0.0",
    [string]$VectorBackend = "local",
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$RunDir = Join-Path $RootDir ".run"
$LogDir = Join-Path $RootDir "logs"
$BackendPidFile = Join-Path $RunDir "backend.pid"
$FrontendPidFile = Join-Path $RunDir "frontend.pid"
$BackendLog = Join-Path $LogDir "backend.log"
$BackendErrLog = Join-Path $LogDir "backend.err.log"
$FrontendLog = Join-Path $LogDir "frontend.log"
$FrontendErrLog = Join-Path $LogDir "frontend.err.log"

function Write-SlcLog {
    param([string]$Message)
    Write-Host "[smart-labor] $Message"
}

function Fail {
    param([string]$Message)
    throw "[smart-labor] ERROR: $Message"
}

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Get-ProjectPython {
    if ($env:PYTHON_BIN -and (Test-Path $env:PYTHON_BIN)) {
        return $env:PYTHON_BIN
    }
    $ragPython = "E:\anaconda\envs\RAG\python.exe"
    if (Test-Path $ragPython) {
        return $ragPython
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }
    Fail "Python not found. Set PYTHON_BIN or install/use the RAG conda env."
}

function Resolve-FreePort {
    param([int]$PreferredPort, [string]$Name)
    for ($port = $PreferredPort; $port -lt ($PreferredPort + 50); $port++) {
        $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if (-not $listeners) {
            if ($port -ne $PreferredPort) {
                Write-SlcLog "$Name port $PreferredPort is busy; using port $port instead."
            }
            return $port
        }
    }
    Fail "No free port found for $Name from $PreferredPort to $($PreferredPort + 49)."
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
    param([string]$Name, [string]$Url, [string]$LogFile, [string]$ErrLogFile, [int]$Seconds = 60)
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-HttpReady $Url) {
            Write-SlcLog "$Name ready: $Url"
            return
        }
        Start-Sleep -Seconds 1
    }
    if (Test-Path $LogFile) {
        Get-Content $LogFile -Tail 40
    }
    if (Test-Path $ErrLogFile) {
        Get-Content $ErrLogFile -Tail 40
    }
    Fail "$Name was not ready within ${Seconds}s. See logs: $LogFile / $ErrLogFile"
}

function Start-LoggedProcess {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$StdoutFile,
        [string]$StderrFile
    )
    if (Test-Path $StdoutFile) {
        Clear-Content -Path $StdoutFile -ErrorAction SilentlyContinue
    }
    if (Test-Path $StderrFile) {
        Clear-Content -Path $StderrFile -ErrorAction SilentlyContinue
    }
    return Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdoutFile `
        -RedirectStandardError $StderrFile `
        -WindowStyle Hidden `
        -PassThru
}

function Test-BackendDeps {
    param([string]$PythonBin)
    $missing = Get-MissingBackendDeps -PythonBin $PythonBin
    return ($missing.Count -eq 0)
}

function Get-MissingBackendDeps {
    param([string]$PythonBin)
    $modules = @(
        "typing_extensions",
        "click",
        "fastapi",
        "uvicorn",
        "pymysql",
        "sqlalchemy",
        "pydantic",
        "pydantic_settings",
        "jose",
        "passlib",
        "multipart"
    )
    $missing = @()
    foreach ($module in $modules) {
        $tmp = [System.IO.Path]::GetTempFileName()
        $cmd = "`"$PythonBin`" -c `"import $module`" 1>`"$tmp`" 2>&1"
        cmd.exe /d /c $cmd | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $output = Get-Content -Path $tmp -ErrorAction SilentlyContinue
            $message = ($output | Select-Object -Last 1).ToString().Trim()
            if (-not $message) {
                $message = "import failed"
            }
            $missing += "${module}: $message"
        }
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    return $missing
}

function Test-FrontendDeps {
    return (Test-Path (Join-Path $FrontendDir "node_modules"))
}

function Assert-ProjectDepsReady {
    param([string]$PythonBin)
    if ($InstallDeps) {
        return
    }
    $backendMissing = Get-MissingBackendDeps -PythonBin $PythonBin
    $frontendReady = Test-FrontendDeps
    if ($backendMissing.Count -eq 0 -and $frontendReady) {
        return
    }
    if ($backendMissing.Count -gt 0) {
        Write-SlcLog "Backend deps are missing in the selected Python env:"
        foreach ($item in $backendMissing) {
            Write-Host "  - $item"
        }
    }
    if (-not $frontendReady) {
        Write-SlcLog "Frontend deps are missing: frontend\node_modules not found."
    }
    Write-Host ""
    Write-Host "Run this once from the project root:"
    Write-Host "  .\start_project.bat -InstallDeps"
    Write-Host ""
    Fail "Dependencies are missing; install them before starting the project."
}

function Ensure-BackendDeps {
    param([string]$PythonBin)
    $missing = Get-MissingBackendDeps -PythonBin $PythonBin
    if ($missing.Count -eq 0) {
        return
    }
    if (-not $InstallDeps) {
        Fail "Backend deps are missing. Run: .\start_project.bat -InstallDeps"
    }
    Write-SlcLog "Backend deps missing before install:"
    foreach ($item in $missing) {
        Write-Host "  - $item"
    }
    Write-SlcLog "Installing backend deps..."
    $requirementsFile = Join-Path $BackendDir "requirements-runtime.txt"
    if ($VectorBackend.ToLower() -eq "milvus") {
        $requirementsFile = Join-Path $BackendDir "requirements.txt"
    }
    Write-SlcLog "Requirements: $requirementsFile"
    & $PythonBin -m pip install --no-user -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        Fail "Backend dependency installation failed."
    }
}

function Ensure-FrontendDeps {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) {
        Fail "npm not found. Install Node.js first."
    }
    if (Test-FrontendDeps) {
        return
    }
    if (-not $InstallDeps) {
        Fail "Frontend deps are missing. Run: .\start_project.bat -InstallDeps"
    }
    Write-SlcLog "Installing frontend deps..."
    Push-Location $FrontendDir
    try {
        & npm.cmd install
        if ($LASTEXITCODE -ne 0) {
            Fail "Frontend dependency installation failed."
        }
    } finally {
        Pop-Location
    }
}

function Start-Backend {
    param([string]$PythonBin)
    $script:BackendPort = Resolve-FreePort -PreferredPort $BackendPort -Name "Backend API"
    Ensure-BackendDeps -PythonBin $PythonBin
    $env:PHASE2_VECTOR_BACKEND = $VectorBackend
    if ($VectorBackend.ToLower() -eq "milvus") {
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
    if (-not $env:DB_BACKEND -or $env:DB_BACKEND -eq "mysql") {
        $env:DB_BACKEND = "sqlite"
    }
    if (-not $env:SQLITE_PATH) {
        $env:SQLITE_PATH = "storage/slc_phase2.db"
    }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $BackendLog -Value "`n== $timestamp start backend on ${BackendHost}:${BackendPort}, vector=${VectorBackend} =="
    Write-SlcLog "Starting backend API..."
    $args = "-m uvicorn app.main:app --host $BackendHost --port $BackendPort"
    $process = Start-LoggedProcess -FilePath $PythonBin -Arguments $args -WorkingDirectory $BackendDir -StdoutFile $BackendLog -StderrFile $BackendErrLog
    Set-Content -Path $BackendPidFile -Value $process.Id
    Wait-HttpReady -Name "Backend API" -Url "http://127.0.0.1:$BackendPort/health" -LogFile $BackendLog -ErrLogFile $BackendErrLog -Seconds 80
}

function Start-Frontend {
    $script:FrontendPort = Resolve-FreePort -PreferredPort $FrontendPort -Name "Frontend"
    Ensure-FrontendDeps
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npm) {
        Fail "npm.cmd not found. Install Node.js first."
    }
    $env:VITE_API_PROXY_TARGET = "http://127.0.0.1:$BackendPort"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $FrontendLog -Value "`n== $timestamp start frontend on ${FrontendHost}:${FrontendPort}, proxy=$env:VITE_API_PROXY_TARGET =="
    Write-SlcLog "Starting frontend..."
    $args = "run dev -- --host $FrontendHost --port $FrontendPort"
    $process = Start-LoggedProcess -FilePath $npm.Source -Arguments $args -WorkingDirectory $FrontendDir -StdoutFile $FrontendLog -StderrFile $FrontendErrLog
    Set-Content -Path $FrontendPidFile -Value $process.Id
    Wait-HttpReady -Name "Frontend" -Url "http://127.0.0.1:$FrontendPort" -LogFile $FrontendLog -ErrLogFile $FrontendErrLog -Seconds 80
}

Ensure-Dir $RunDir
Ensure-Dir $LogDir

$PythonBin = Get-ProjectPython
Write-SlcLog "Project root: $RootDir"
Write-SlcLog "Python: $PythonBin"
Write-SlcLog "Vector backend: $VectorBackend"

Assert-ProjectDepsReady -PythonBin $PythonBin
Start-Backend -PythonBin $PythonBin
Start-Frontend

Write-SlcLog "Started."
Write-Host "Frontend: http://localhost:$FrontendPort"
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "API docs: http://127.0.0.1:$BackendPort/docs"
Write-Host "Logs:     $LogDir"
