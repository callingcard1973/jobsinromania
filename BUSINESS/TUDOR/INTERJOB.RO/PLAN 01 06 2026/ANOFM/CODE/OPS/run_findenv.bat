@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\find_env.ps1" -H 192.168.100.21
timeout /t 5
