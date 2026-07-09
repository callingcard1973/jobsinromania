@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\fix_and_ingest.ps1"
timeout /t 5
