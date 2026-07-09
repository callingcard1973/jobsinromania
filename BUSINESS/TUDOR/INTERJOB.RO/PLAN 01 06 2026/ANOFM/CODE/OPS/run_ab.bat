@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\check_ab.ps1" -H 192.168.100.20
powershell -ExecutionPolicy Bypass -File ".\check_ab.ps1" -H 192.168.100.21
timeout /t 5
