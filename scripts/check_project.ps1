param(
    [string]$PythonBin = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

function Write-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail = "")
    if ($Ok) {
        Write-Host "[OK]   $Name $Detail"
    } else {
        Write-Host "[MISS] $Name $Detail"
    }
}

function Get-ProjectPython {
    if ($PythonBin -and (Test-Path $PythonBin)) {
        return $PythonBin
    }
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
    return ""
}

function Get-MissingBackendDeps {
    param([string]$Python)
    if (-not $Python) {
        return @("python executable not found")
    }
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
        $cmd = "`"$Python`" -c `"import $module`" 1>`"$tmp`" 2>&1"
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

$python = Get-ProjectPython
Write-Host "Project: $RootDir"
Write-Host "Python:  $python"
Write-Host ""

$backendMissing = Get-MissingBackendDeps -Python $python
Write-Check "backend python deps" ($backendMissing.Count -eq 0)
foreach ($item in $backendMissing) {
    Write-Host "       - $item"
}

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
Write-Check "npm.cmd" ($null -ne $npm) ($(if ($npm) { $npm.Source } else { "" }))

$nodeModules = Test-Path (Join-Path $FrontendDir "node_modules")
Write-Check "frontend node_modules" $nodeModules

$runtimeReq = Test-Path (Join-Path $BackendDir "requirements-runtime.txt")
Write-Check "backend requirements-runtime.txt" $runtimeReq

$packageJson = Test-Path (Join-Path $FrontendDir "package.json")
Write-Check "frontend package.json" $packageJson

Write-Host ""
if ($backendMissing.Count -eq 0 -and $npm -and $nodeModules) {
    Write-Host "Environment looks ready. Start with:"
    Write-Host "  .\start_project.bat"
} else {
    Write-Host "Install missing dependencies and start with:"
    Write-Host "  .\start_project.bat -InstallDeps"
}
