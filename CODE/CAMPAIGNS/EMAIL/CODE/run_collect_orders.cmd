@echo off
REM Order Collector - Run from laptop
REM Requires: LM Studio running on localhost:1234 with a model loaded
REM Usage: run_collect_orders.cmd [--dry-run] [--reprocess]

cd /d "D:\MEMORY\EMAIL"

REM Check LM Studio
curl -s --connect-timeout 3 http://localhost:1234/v1/models >nul 2>&1
if errorlevel 1 (
    echo [WARN] LM Studio not running - will use regex fallback
    echo        Start LM Studio and load gemma-2-2b-it for best results
)

python collect_orders.py %*

echo.
echo Output: D:\MEMORY\EMAIL\orders.csv
echo Log:    D:\MEMORY\EMAIL\orders_collector.log
pause
