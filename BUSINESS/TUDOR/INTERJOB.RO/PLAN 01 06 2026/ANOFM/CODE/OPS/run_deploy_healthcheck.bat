@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\deploy_healthcheck.ps1"
timeout /t 5
