@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\raspi_task2_health.ps1"
timeout /t 5
