@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\inspect_env_usage.ps1"
timeout /t 5
