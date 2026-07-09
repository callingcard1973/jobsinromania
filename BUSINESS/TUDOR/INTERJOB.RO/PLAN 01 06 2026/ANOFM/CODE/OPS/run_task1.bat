@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\raspi_task1_archive.ps1"
timeout /t 5
