@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_production_backend.ps1" %*
exit /b %ERRORLEVEL%
