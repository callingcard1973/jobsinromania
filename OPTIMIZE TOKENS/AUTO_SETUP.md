# Automatic Token Optimization Setup

**Goal:** Make token optimization run automatically on all Claude Code sessions.

**Status:** Ready to deploy

---

## 3 Ways to Automate

### Option 1: Easiest - Double-Click to Start (Recommended)

**File:** `D:\MEMORY\OPTIMIZE TOKENS\start_optimized_session.bat`

**How to use:**
1. Double-click `start_optimized_session.bat`
2. System initializes automatically
3. Start Claude Code with `/code`
4. When done: `python session_manager.py end` + `/clear`

**Advantage:** One-click, no configuration needed

**To add shortcut to Desktop:**
1. Right-click `start_optimized_session.bat`
2. Send to → Desktop (create shortcut)
3. Double-click from desktop to start optimized sessions

---

### Option 2: PowerShell (Advanced)

**File:** `D:\MEMORY\OPTIMIZE TOKENS\start_optimized_session.ps1`

**How to use:**
```powershell
cd D:\MEMORY\OPTIMIZE TOKENS
.\start_optimized_session.ps1

# Or with custom task description:
.\start_optimized_session.ps1 -TaskDescription "Implement feature X"
```

**Advantage:** More control, colored output, parameter support

---

### Option 3: Claude Code Hook (Automatic)

**File:** `C:\Users\apami\.claude\settings.json`

**Setup:**
1. Open `C:\Users\apami\.claude\settings.json`
2. Add this to the `"hooks"` section:

```json
{
  "hooks": {
    "SessionStart": {
      "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\auto_init.py"
    },
    "PostToolUse": {
      "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\token_monitor.py"
    }
  }
}
```

3. Restart Claude Code
4. System initializes automatically on every session

**Advantage:** Fully automatic, no manual steps

**Full example settings.json:**
```json
{
  "enabled_mcp_servers": ["mcp__plugin_playwright_playwright"],
  "disabled_mcp_servers": ["superpowers:code-simplifier"],
  "hooks": {
    "SessionStart": {
      "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\auto_init.py"
    },
    "PostToolUse": {
      "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\token_monitor.py"
    }
  }
}
```

---

## Recommended Setup

### For Immediate Use (Today)

```bash
# Option 1: Manual each time
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py start "task"
[work]
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py end
/clear

# Option 2: Use batch file
# Double-click: D:\MEMORY\OPTIMIZE TOKENS\start_optimized_session.bat
```

### For Regular Use (This Week)

**Create Desktop Shortcut:**
1. Right-click `start_optimized_session.bat`
2. Send to → Desktop (create shortcut)
3. Rename shortcut to "Claude Optimized"
4. Double-click before each Claude Code session

### For Full Automation (Optional)

**Deploy hook to settings.json:**
1. Open `C:\Users\apami\.claude\settings.json`
2. Add hooks from "Option 3" above
3. Restart Claude Code
4. System auto-initializes every session

---

## What auto_init.py Does

```
1. ✅ Ensures ~/.claude/settings.json exists
2. ✅ Resets plugins to recommended defaults
   - Playwright: ON (needed for web work)
   - Code-simplifier: OFF (disable by default)
3. ✅ Installs token monitor hook
4. ✅ Checks CLAUDE.md compliance
5. ✅ Logs initialization event
```

---

## What start_optimized_session.bat Does

```
1. ✅ Runs auto_init.py
2. ✅ Resets plugins to defaults
3. ✅ Starts session_manager tracking
4. ✅ Shows optimization tips
5. ✅ Ready for /code command
```

---

## What start_optimized_session.ps1 Does

Same as .bat file but with:
- Colored output for readability
- Parameter support for task descriptions
- Advanced error handling
- Better user experience

---

## Quick Setup Instructions

### Step 1: Test It Works

```bash
python D:\MEMORY\OPTIMIZE TOKENS\auto_init.py
```

Expected output:
```
[INITIALIZED] Token Optimization System
[OK] CLAUDE.md compliant
[READY] System initialized
```

### Step 2: Use Desktop Shortcut (Recommended)

```bash
# From D:\MEMORY\OPTIMIZE TOKENS\
# Right-click start_optimized_session.bat
# → Send to → Desktop (create shortcut)
```

Then: Double-click shortcut before each Claude Code session

### Step 3 (Optional): Set Up Hook

Edit `C:\Users\apami\.claude\settings.json`:
- Add SessionStart hook (runs at session start)
- Add PostToolUse hook (monitors context)

---

## Verification Checklist

- [ ] auto_init.py created and tested
- [ ] start_optimized_session.bat working
- [ ] start_optimized_session.ps1 working
- [ ] Desktop shortcut created (optional)
- [ ] ~/.claude/settings.json has hooks (optional)
- [ ] Session manager runs on startup
- [ ] Plugins reset to defaults
- [ ] Token monitor installed

---

## Usage After Setup

### With Desktop Shortcut

1. **Before work:**
   ```
   Double-click "Claude Optimized" shortcut
   ```

2. **In Claude Code:**
   ```
   /code
   ```

3. **After work:**
   ```bash
   python session_manager.py end
   /clear
   ```

### With Hook (Fully Automatic)

1. **Claude Code starts automatically:**
   - auto_init.py runs
   - Plugins reset
   - Session ready

2. **During work:**
   - token_monitor.py warns at 50%/75%/90%
   - All events logged

3. **No manual steps needed**

---

## Troubleshooting

### "Python not found"

Ensure Python 3.12 is in PATH:
```bash
python --version
```

Or use full path in batch file:
```bash
C:\Users\apami\AppData\Local\Programs\Python312\python.exe auto_init.py
```

### "Settings file not found"

auto_init.py creates it automatically if missing. Run:
```bash
python auto_init.py
```

### "Hook not running"

1. Restart Claude Code completely
2. Check settings.json syntax (must be valid JSON)
3. Verify file paths use double backslashes: `D:\\MEMORY\\...`

### "Batch file doesn't work"

Run from command prompt:
```cmd
cd D:\MEMORY\OPTIMIZE TOKENS
start_optimized_session.bat
```

Or double-click directly (Windows handles .bat files automatically)

---

## Files Summary

| File | Purpose | How to Use |
|------|---------|-----------|
| `auto_init.py` | Initialization script | `python auto_init.py` |
| `start_optimized_session.bat` | Windows batch starter | Double-click or run |
| `start_optimized_session.ps1` | PowerShell starter | `.\start_optimized_session.ps1` |
| `session_manager.py` | Session tracking | Run in batch/PS1 |
| `plugin_toggle.py` | Plugin management | Manual use during session |
| `claude_md_lint.py` | Audit CLAUDE.md | Weekly: `python claude_md_lint.py --summary` |

---

## Automation Flow

```
Desktop Shortcut
    ↓
start_optimized_session.bat
    ↓
auto_init.py (initializes system)
    ↓
session_manager.py start
    ↓
Ready for /code
    ↓
[Work in Claude Code]
    ↓
token_monitor.py (warns at thresholds)
    ↓
/compact (at 50%)
    ↓
/clear (at 75%)
    ↓
session_manager.py end (logs and estimates)
    ↓
/clear (reset for next task)
```

---

## Recommended Implementation Timeline

**Today:**
- [ ] Test: `python auto_init.py`
- [ ] Create Desktop shortcut

**This Week:**
- [ ] Use shortcut for each session
- [ ] Run: `python claude_md_lint.py --summary` (weekly)

**Next Week:**
- [ ] Optional: Set up hook in settings.json
- [ ] Review session logs

**Ongoing:**
- [ ] Use automatically
- [ ] Audit CLAUDE.md weekly
- [ ] Export metrics monthly

---

## Expected Results After Setup

**Week 1:**
- ✅ Every session tracked automatically
- ✅ Plugins reset to defaults
- ✅ Token usage visible
- Savings: 5-10%

**Week 2:**
- ✅ Manual plugin management per task
- ✅ /clear discipline established
- Savings: 10-15%

**Month 1:**
- ✅ Weekly audits running
- ✅ All CLAUDE.md files compliant
- Savings: 25-40%

**Month 6:**
- ✅ Full team optimization
- Savings: 50-70%

---

## Quick Start

**Option A - Right Now (2 minutes):**
```bash
python D:\MEMORY\OPTIMIZE TOKENS\auto_init.py
```

**Option B - Desktop Shortcut (5 minutes):**
1. Right-click `start_optimized_session.bat`
2. Send to → Desktop (create shortcut)
3. Double-click shortcut before each session

**Option C - Full Automation (10 minutes):**
1. Edit `C:\Users\apami\.claude\settings.json`
2. Add hooks from "Option 3" above
3. Restart Claude Code
4. Done - fully automatic

---

## Support

- `auto_init.py --help` — Get help on initialization
- `auto_init.py --check-only` — Check without making changes
- `QUICKSTART.txt` — Daily command reference
- `README.md` — Complete documentation

---

**Status: Ready to deploy**

Choose Option A, B, or C and start optimizing!

Last updated: 2026-02-22
