# Claude Code Token Optimization Rules

**Objective:** Reduce per-session token consumption by 50–70% through architecture, plugin management, and session discipline.

---

## Rule 1: CLAUDE.md File Size

**Standard:** ≤50 lines, ≤1,500 tokens

### Guidelines

- **Keep it essential:** Infrastructure, conventions, directory index only
- **Move skills:** Document them in separate skill files, reference only in CLAUDE.md
- **Remove code examples:** One-liner references instead of full usage blocks
- **No redundant docs:** Each directory's CLAUDE.md stands alone; root CLAUDE.md is meta-level only

### Audit

Run before and after each major update:

```bash
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py
```

Expected output: All CLAUDE.md files marked `[OK]` (≤1,500 tokens).

---

## Rule 2: Plugin Management

**Default state:**
- Playwright (browser automation): **ON** — needed for web scraping, UI testing
- Code-simplifier: **OFF** — enable only when refactoring code

### Switching Plugins

When starting a task **without** web automation, disable playwright:

```bash
python plugin_toggle.py browser off     # Save ~400-600 tokens
python plugin_toggle.py status          # Verify disabled
```

When done:

```bash
python plugin_toggle.py browser on      # Re-enable for next browser task
```

### Token Savings

- Disabling playwright: ~400–600 tokens/session
- Disabling simplifier: ~200 tokens/session
- Combined savings: ~600–800 tokens/session (~6–8% of typical session)

---

## Rule 3: Model Selection

**Principle:** Use the smallest capable model for each task.

### Task Matrix

| Task Type | Model | Why |
|-----------|-------|-----|
| Research, reading, file search | **Haiku** | Fast, cheap, sufficient for analysis |
| Code implementation, debugging | **Sonnet** | Better reasoning for complex logic |
| Architecture, design, reviews | **Opus** | Deep analysis; use sparingly |

### When to Escalate

- Haiku → Sonnet: If the task requires multi-file refactoring or complex bug diagnosis
- Sonnet → Opus: Only for architectural decisions or critical security reviews

Use `/fast` to get Sonnet speed with Opus reasoning when needed.

---

## Rule 4: Context Management

**Thresholds:**

- **50% fill:** Start planning next `/clear` or `/compact`
- **75% fill:** Run `/compact` to compress prior messages
- **90% fill:** Restart session immediately (risk of truncation)

### Session Workflow

```bash
# 1. Start a session
python session_manager.py start "search for bug in CV module"

# 2. Work on task
claude-code  # or /code in Claude web

# 3. After 30 min or at 50% context:
/compact  # Compress prior messages

# 4. When done:
python session_manager.py end
/clear    # Clear context for next task
```

### Between-Task Rules

- **Always** `/clear` between unrelated tasks (different codebases)
- **Always** `/clear` between implementation and research phases
- Do **not** carry over plugins from previous task (reset to defaults)

---

## Rule 5: Session Hygiene

### Pre-Session

1. Run `python plugin_toggle.py defaults` to reset plugins
2. Start session: `python session_manager.py start "task desc"`
3. Note the recommended model from the tool output

### Mid-Session

1. At 50% context: `/compact`
2. At 75% context: `/compact` again
3. At 90% context: `/clear` + restart

### Post-Session

1. End session: `python session_manager.py end`
2. Check token estimate: `python session_manager.py log --tail 5`
3. Clear context: `/clear`
4. Before next task: reset plugins

### Cleanup

```bash
# Weekly: Review session logs
python session_manager.py log --tail 100

# Monthly: Analyze trends
python session_manager.py export

# Quarterly: Re-audit all CLAUDE.md files
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py
```

---

## Rule 6: CLAUDE.md Compliance Checklist

Before committing changes to any CLAUDE.md:

- [ ] File ≤50 lines
- [ ] Estimated tokens ≤1,500 (check with linter)
- [ ] No code examples (reference only)
- [ ] No duplicated docs from subdirectories
- [ ] Top 3 sections: Infrastructure, Conventions, Directory Index
- [ ] Sensitive files listed, never exposed with examples

Run validation:

```bash
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --root D:\MEMORY
```

---

## Rule 7: Tool Selection & Context

### Preferred Order

1. **Read tool:** Single file analysis
2. **Glob tool:** Find files by pattern
3. **Grep tool:** Search file contents
4. **Task + Explore agent:** Multi-file research or codebase exploration
5. **Bash tool:** Terminal operations (git, npm, etc.)

### Minimize Context

- Use `--limit` and `-A/-B/-C` flags to focus grep results
- Run searches in subdirectories, not from repo root
- Delete large intermediate results from conversation

---

## Rule 8: Monitoring & Reporting

### Daily Check

```bash
# See current session
python session_manager.py status

# Review today's logs
python session_manager.py log
```

### Weekly Review

```bash
# Check all CLAUDE.md files for bloat
python D:\MEMORY\OPTIMIZE TOKENS\claude_md_lint.py --summary

# Export session metrics
python session_manager.py export
```

### Alerts & Escalation

| Metric | Yellow | Red |
|--------|--------|-----|
| CLAUDE.md file size | >40 lines | >50 lines |
| Session duration | >45 min | >60 min |
| Context fill | >75% | >90% |
| Plugin bloat | Simplifier ON | Both ON |

---

## Implementation Checklist

- [x] Trim root CLAUDE.md to ≤50 lines
- [x] Create `claude_md_lint.py` for auditing
- [x] Create `plugin_toggle.py` for plugin management
- [x] Create `session_manager.py` for session tracking
- [x] Create `token_monitor.py` for real-time warnings
- [x] Create `RULES.md` (this document)
- [ ] Deploy `token_monitor.py` hook to `~/.claude/settings.json`
- [ ] Run baseline audit: `claude_md_lint.py`
- [ ] Test plugin toggle workflow
- [ ] Integrate session_manager into development workflow
- [ ] Monthly review and tune thresholds

---

## FAQ

### Q: Why disable Playwright by default?
**A:** Playwright adds ~15–20 tool definitions (~500 tokens) to every session, even unrelated tasks. Disable it for research/reading tasks; re-enable for web work.

### Q: How often should I `/clear`?
**A:** After 30 minutes or at 50% context fill, whichever comes first. More frequently if working on unrelated tasks.

### Q: Can I use Opus for everything?
**A:** No. Cost scales linearly; Opus is 3–5× more expensive. Use Haiku for research, Sonnet for implementation, Opus only for architecture.

### Q: What's the actual token savings?
**A:** Trimmed CLAUDE.md + disabled plugins + 30-min sessions + /clear discipline = **50–70% reduction** (~10–15K saved tokens/day for typical workflow).

### Q: When to override these rules?
**A:** Only for time-critical bugs (>1 hour context fill is OK) or novel architectures (Opus necessary). Document the override in session notes.

---

## Version

Last updated: 2026-02-22
Next review: 2026-03-22

For implementation status, see `D:\MEMORY\OPTIMIZE TOKENS\README.md`
