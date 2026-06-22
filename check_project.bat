@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_project.ps1" %*
exit /b %ERRORLEVEL%
