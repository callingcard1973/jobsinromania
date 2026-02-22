#requires -version 3.0
<#
.SYNOPSIS
    Token Optimization - Automated Session Starter for PowerShell

.DESCRIPTION
    Initializes token optimization system and starts a tracked session.
    Runs auto-init, resets plugins, and logs session start.

.PARAMETER TaskDescription
    Description of the task you're about to do (optional)
    If not provided, uses "Claude Code session" as default

.EXAMPLE
    .\start_optimized_session.ps1
    # Starts default session

.EXAMPLE
    .\start_optimized_session.ps1 -TaskDescription "Implement user authentication"
    # Starts session with specific task description

.NOTES
    Location: D:\MEMORY\OPTIMIZE TOKENS\start_optimized_session.ps1
#>

param(
    [Parameter(Position=0)]
    [string]$TaskDescription = "Claude Code session"
)

# Colors
$ColorGreen = [System.ConsoleColor]::Green
$ColorYellow = [System.ConsoleColor]::Yellow
$ColorRed = [System.ConsoleColor]::Red
$ColorCyan = [System.ConsoleColor]::Cyan

function Write-Header {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor $ColorCyan
    Write-Host "                    TOKEN OPTIMIZATION - SESSION STARTER" -ForegroundColor $ColorCyan
    Write-Host "================================================================================" -ForegroundColor $ColorCyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[$($args[1])/$($args[2])] $Message" -ForegroundColor $ColorGreen
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $ColorYellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ColorRed
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $ColorGreen
}

# Start
Write-Header

# Step 1: Initialize
Write-Step "Initializing token optimization system..." 1 4
Set-Location "D:\MEMORY\OPTIMIZE TOKENS"

try {
    $output = & python auto_init.py --reset-plugins 2>&1
    Write-Host $output
} catch {
    Write-Error-Custom "Initialization failed: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 2: Start session
Write-Step "Starting session tracking..." 2 4
try {
    $output = & python session_manager.py start "$TaskDescription" 2>&1
    Write-Host $output
} catch {
    Write-Error-Custom "Session manager failed: $_"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 3: Summary
Write-Step "Session initialized successfully" 3 4

Write-Host ""
Write-Host "================================================================================" -ForegroundColor $ColorCyan
Write-Host "OPTIMIZATION TIPS FOR THIS SESSION:" -ForegroundColor $ColorCyan
Write-Host "================================================================================" -ForegroundColor $ColorCyan
Write-Host ""
Write-Host "   * Use /clear between different tasks"
Write-Host "   * Use /compact at 50% context fill"
Write-Host "   * Check status: python plugin_toggle.py status"
Write-Host "   * Disable browser (if not needed): python plugin_toggle.py browser off"
Write-Host "   * Re-enable browser: python plugin_toggle.py browser on"
Write-Host "   * View logs: python session_manager.py log --tail 20"
Write-Host ""
Write-Host "================================================================================" -ForegroundColor $ColorCyan
Write-Host ""

# Step 4: Ready
Write-Step "Ready to work" 4 4
Write-Host ""
Write-Host "Next steps:"
Write-Host "   1. Start Claude Code: /code"
Write-Host "   2. Work normally"
Write-Host "   3. When done, run:"
Write-Host "      python session_manager.py end"
Write-Host "      /clear"
Write-Host ""

Write-Success "Token optimization system is active!"
Write-Host ""
Read-Host "Press Enter to continue"
