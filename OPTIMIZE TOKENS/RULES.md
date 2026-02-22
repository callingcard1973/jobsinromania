# Token Optimization Rules

**Goal:** Reduce per-session token consumption through CLAUDE.md discipline, plugin management, and session hygiene.

---

## Rule 1: CLAUDE.md — ≤50 lines, ≤1,500 tokens

- Keep essential: infrastructure, conventions, directory index only
- No code examples, no duplicated subdirectory docs
- Audit: `python claude_md_lint.py --root D:\MEMORY`

## Rule 2: Plugin Management

**Defaults:** Playwright ON, Code-simplifier OFF.

```bash
python plugin_toggle.py status          # Check state
python plugin_toggle.py browser off     # Save ~500 tokens (no web task)
python plugin_toggle.py defaults        # Restore defaults
```

## Rule 3: Model Selection

| Task | Model |
|------|-------|
| Research, file search | Haiku |
| Implementation, debugging | Sonnet |
| Architecture, security review | Opus |

Use `/fast` for Sonnet-speed Opus reasoning.

## Rule 4: Context Management

| Fill | Action |
|------|--------|
| 50% | Plan /compact |
| 75% | Run /compact now |
| 90% | /clear and restart |

Always /clear between unrelated tasks.

## Rule 5: Session Workflow

```bash
# Before session
python auto_init.py                    # Check CLAUDE.md + plugins + reset counter

# During session
python token_monitor.py                # Check estimated context usage

# After session
python session_manager.py end          # Log duration
```

## Rule 6: Tool Selection

1. Read → single file
2. Glob → find by pattern
3. Grep → search contents (use -A/-B/--limit)
4. Task + Explore → multi-file research
5. Bash → terminal ops only

Search in subdirectories, not repo root.

## Rule 7: What Actually Saves Tokens

| Action | Savings |
|--------|---------|
| Trimmed CLAUDE.md (50→50 lines) | ~200-400 tokens/session |
| Disable unused plugins | ~200-600 tokens/session |
| /clear between tasks | Prevents context overflow |
| /compact at 50% fill | Extends session life |
| Haiku for research subagents | 3-5x cheaper per call |

**Hooks don't work** — Claude Code doesn't expose context metrics. Use manual checks.

---

Last updated: 2026-02-22
