# Token-Free Save — save_context.py

Saves session state to octogent tentacle todo.md **without using Claude API tokens**.

## Modes

### Mode 1: Token-Heavy (original, uses Claude)
```bash
python save_context.py "<tentacle>" "<summary>"
```
- You write/provide the summary
- Summary gets saved
- **Cost:** ~500-2000 tokens (if you ask Claude to generate the summary first)

### Mode 2: Token-Free (NEW, zero cost)
```bash
python save_context.py --local <tentacle>
```
- Auto-generates summary from git state
- No Claude involved
- **Cost:** 0 tokens
- Output includes: changed files, new files, recent commits

## Example

```bash
cd D:\MEMORY\BUSINESS\OVIDIU PACALA

# Auto-detect tentacle + save (no tokens)
python D:/MEMORY/CODE/INFRA/OCTOGENT/save_context.py --local business-ops

# Saved to business-ops/todo.md [TOKEN-FREE]
```

## Git-based Summary Content

When using `--local`, summary includes:
- Changed files (last 5, with count of others)
- New/untracked files (last 3, with count of others)
- Recent commits (last 5)
- Timestamp + tentacle label

Example:
```
## Session 2026-04-19 14:27
**Auto-generated from git [NO TOKENS USED]**

Changed: file1.py, file2.md, CLAUDE.md (+2 more)
New: memory.md, notes.txt

Recent commits:
```
commit-hash1 message
commit-hash2 message
```
```

## Use Cases

| Scenario | Mode | Why |
|----------|------|-----|
| End-of-session save (routine) | `--local` | Fast, free, captures what changed |
| Need detailed notes | Token-heavy | Provide custom summary for context |
| Stop hook (auto-save) | `--local` | Never blocks, zero cost |
| Quick checkpoint | `--local` | Git tells you what you did |

## Integration

### In settings.json (auto-save on stop)
```json
{
  "hooks": {
    "SessionStop": {
      "run": "python D:/MEMORY/CODE/INFRA/OCTOGENT/save_context.py --local $(python D:/MEMORY/CODE/INFRA/OCTOGENT/save_context.py --detect)"
    }
  }
}
```

### Or via /save skill
When prompted for summary, use:
```
/local <tentacle>
```
to trigger token-free mode.

## Files

- `save_context.py` — Main script (both modes)
- `save_context_local.py` — Standalone token-free version (optional)

## Tentacle Mapping

Auto-detected from `CWD`. See `save_context.py` PATTERN_MAP for full list:
- `BUSINESS/*` → `business-ops`
- `CODE/INFRA` → `infra`
- `CODE/CAMPAIGNS` → `campaigns`
- `CODE/INFRA/AUTOMATE` → `ai-agents`
- etc.
