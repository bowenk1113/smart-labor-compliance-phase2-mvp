@echo off
setlocal
call "%~dp0scripts\stop_project.bat" %*
exit /b %ERRORLEVEL%

