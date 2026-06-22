@echo off
setlocal
call "%~dp0scripts\start_project.bat" %*
exit /b %ERRORLEVEL%

