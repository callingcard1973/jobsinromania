@echo off
cd /d "%~dp0"
echo ============================================
echo  Inspectez ANOFM pe raspibig (192.168.100.21)
echo ============================================
powershell -ExecutionPolicy Bypass -File ".\inspect_anofm_raspi.ps1" -RaspiHost 192.168.100.21 -Pw RASPI_PW_REDACTED
echo.
echo ============================================
echo  Inspectez ANOFM pe raspi backup (192.168.100.20)
echo ============================================
powershell -ExecutionPolicy Bypass -File ".\inspect_anofm_raspi.ps1" -RaspiHost 192.168.100.20 -Pw RASPI_PW_REDACTED
echo.
echo === TERMINAT. Rapoartele sunt in DATA\RASPI\ ===
timeout /t 8
