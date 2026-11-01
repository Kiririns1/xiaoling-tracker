@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_pc.ps1" %*
pause
