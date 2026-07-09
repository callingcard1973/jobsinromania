@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\inspect_raspi_ingest.ps1"
timeout /t 5
