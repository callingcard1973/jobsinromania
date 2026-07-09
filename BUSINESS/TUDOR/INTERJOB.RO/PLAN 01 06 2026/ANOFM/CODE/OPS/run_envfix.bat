@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\apply_env_fix.ps1"
timeout /t 5
