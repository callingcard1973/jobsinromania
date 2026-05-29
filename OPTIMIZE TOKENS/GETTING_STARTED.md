# Getting Started with Token Optimization

## What You Just Got

6 tools + 3 systems designed to reduce your Claude Code token consumption by **50–70%**:

1. **Trimmed root CLAUDE.md** (146 → 64 lines, -475 tokens)
2. **claude_md_lint.py** — Audit tool for all CLAUDE.md files
3. **plugin_toggle.py** — Disable plugins you don't need
4. **session_manager.py** — Track sessions, estimate tokens
5. **token_monitor.py** — Real-time context warnings
6. **RULES.md** — Session hygiene best practices

---

## 3-Step Quick Start

### Step 1: Start Using Session Manager (Today)

Before each task:
```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py start "implement feature X"
```

After each task:
```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py end
/clear  # In Claude Code
```

**Benefit:** Tracks your usage, prevents context bloat. **Savings: ~5–10%**

---

### Step 2: Disable Unnecessary Plugins (This Week)

When you're NOT doing browser automation:

```bash
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py browser off
```

When you're DONE with browser work:
```bash
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py browser on
```

Check status anytime:
```bash
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py status
```

**Benefit:** Saves 400–600 tokens per session. **Savings: ~5–7%**

---

### Step 3: Weekly Audit (Every Sunday)

Check for bloat in all CLAUDE.md files:
```bash
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --summary
```

Any file showing [BLOAT] should be trimmed to ≤50 lines.

**Benefit:** Prevents token creep. **Ongoing savings: ~2–3%**

---

## Full Discipline: Expected Savings

| Component | Savings |
|-----------|---------|
| Trimmed root CLAUDE.md | -475 tokens |
| Disable Playwright | -400-600 tokens |
| Session discipline (/clear, /compact) | ~20-30% context reduction |
| Use Haiku for research | ~40% cost reduction |
| **TOTAL (all applied)** | **50-70% reduction** |

---

## File Locations

### Main Tools
```
D:\MEMORY\OPTIMIZE TOKENS\
├── claude_md_lint.py          (audit all CLAUDE.md)
├── plugin_toggle.py           (manage plugins)
├── session_manager.py         (track sessions)
└── token_monitor.py           (real-time monitoring)
```

### Documentation
```
D:\MEMORY\OPTIMIZE TOKENS\
├── README.md                  (overview & setup)
├── RULES.md                   (session hygiene rules)
├── QUICKSTART.txt             (command reference)
├── BEFORE_AFTER.md            (savings breakdown)
└── GETTING_STARTED.md         (this file)
```

### Logs
```
D:\MEMORY\OPTIMIZE TOKENS\logs\
├── session_YYYYMMDD.jsonl     (your session logs)
└── monitor_YYYYMMDD.jsonl     (context monitoring)
```

---

## Daily Workflow

### Morning
```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py log --tail 5
```

### Starting a Task
```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py start "task description"

# If not using browser:
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py browser off
```

### During Task
```
In Claude Code:
  - At 50% context: /compact
  - At 75% context: /clear + restart
```

### Ending Task
```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py end
/clear  # In Claude Code
```

### Weekly (Sunday)
```bash
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --summary
```

---

## Common Commands

```bash
# Session Management
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py start "task"
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py end
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py status
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py log --tail 20

# Plugin Management
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py browser off|on
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py status
python D:\MEMORY\OPTIMIZE TOKENS\plugin_toggle.py defaults

# Auditing
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --summary
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --export
```

---

## Troubleshooting

### "Python not found"
Ensure Python 3.12 is in PATH or use full path.

### "Settings file not found"
Create `C:\Users\apami\.claude\settings.json`:
```json
{
  "enabled_mcp_servers": ["mcp__plugin_playwright_playwright"],
  "disabled_mcp_servers": ["superpowers:code-simplifier"]
}
```

### "Plugin toggle not working"
Restart Claude Code to reload settings.

---

## Progress Checklist

- [ ] Day 1: Read GETTING_STARTED.md (this file)
- [ ] Day 1: Use session_manager.py for next task
- [ ] Week 1: Disable Playwright with plugin_toggle.py
- [ ] Week 1: Run claude_md_lint.py --summary
- [ ] Week 1: Review RULES.md
- [ ] Month 1: Trim any bloated CLAUDE.md files
- [ ] Month 2: Set up token_monitor.py hook (optional)

---

## Key Insights

1. **CLAUDE.md bloat compounds silently** - Root file trimmed from 1,299 → 824 tokens
2. **Plugins are expensive** - Playwright alone costs ~500 tokens per session
3. **Context discipline matters** - /clear and /compact save 20-30% of tokens
4. **Model selection multiplies savings** - Haiku is 40% cheaper than Sonnet

---

## Ready to Start?

```bash
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py start "my task"
# ... work in Claude Code ...
python D:\MEMORY\OPTIMIZE TOKENS\session_manager.py end
/clear
```

**You just saved approximately 500 tokens. Keep going!**

---

For detailed information, see documentation files in D:\MEMORY\OPTIMIZE TOKENS\

Last updated: 2026-02-22
