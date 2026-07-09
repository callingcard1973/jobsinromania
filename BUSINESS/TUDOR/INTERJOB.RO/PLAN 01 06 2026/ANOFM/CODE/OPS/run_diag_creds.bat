@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\diag_creds.ps1"
timeout /t 5
