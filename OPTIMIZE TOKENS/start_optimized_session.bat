@echo off
REM Token Optimization - Automated Session Starter for Windows
REM
REM Usage: Double-click this file OR run from command line
REM
REM What it does:
REM   1. Initializes token optimization system
REM   2. Resets plugins to defaults
REM   3. Starts a tracked session
REM   4. Launches Claude Code
REM
REM Location: D:\MEMORY\OPTIMIZE TOKENS\start_optimized_session.bat

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo                  TOKEN OPTIMIZATION - SESSION STARTER
echo ================================================================================
echo.

REM Initialize auto-init system
echo [1/4] Initializing token optimization system...
cd /d "D:\MEMORY\OPTIMIZE TOKENS"
python auto_init.py --reset-plugins

if errorlevel 1 (
    echo [ERROR] Initialization failed
    pause
    exit /b 1
)

REM Start session manager
echo.
echo [2/4] Starting session tracking...

REM Get task description from user or use default
set "task_desc=Claude Code session"

REM Check if argument provided
if not "%~1"=="" (
    set "task_desc=%~1"
)

python session_manager.py start "%task_desc%"

if errorlevel 1 (
    echo [ERROR] Session manager failed
    pause
    exit /b 1
)

echo.
echo [3/4] Session started successfully
echo.
echo ================================================================================
echo OPTIMIZATION TIPS FOR THIS SESSION:
echo ================================================================================
echo.
echo   * Use /clear between different tasks
echo   * Use /compact at 50%% context fill
echo   * Run: python plugin_toggle.py browser off   (for non-browser work)
echo   * Run: python plugin_toggle.py browser on    (to re-enable)
echo   * Check status: python plugin_toggle.py status
echo.
echo ================================================================================
echo.
echo [4/4] Ready to work - use /code in Claude
echo.
echo When done, run:
echo   python session_manager.py end
echo   /clear
echo.
pause
