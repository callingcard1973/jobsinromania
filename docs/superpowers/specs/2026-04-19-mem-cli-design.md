# Design: `mem` — Terminal Project Context CLI

**Date:** 2026-04-19
**Status:** Approved
**Inspired by:** [Octogent mental model](https://github.com/hesamsheikh/octogent/blob/main/docs/concepts/mental-model.md) — file-based context, durable/runtime split

## Purpose

Solve three daily pains in `D:\MEMORY`:
1. **Context retrieval** — remember what each project does on return
2. **Coordination** — track active tasks across 30+ projects
3. **Onboarding** — new agents/people grasp structure fast

A simpler, terminal-only alternative to octogent. No UI, no websockets, no workers. Just files + CLI.

## Scope

In scope:
- Single Python script (`mem.py`), stdlib only
- File-based convention: `PROJECT.md` + `todo.md`
- 8 CLI commands
- Audit + scaffold tool to backfill missing `PROJECT.md` across `D:\MEMORY`

Out of scope (YAGNI):
- Web UI, dashboards
- Multi-terminal coordination (tmux/screen)
- LLM features (summarization, auto-fill)
- Cross-project dependency graphs
- Real-time sync

## Architecture

### File convention (per project)

```
<project-dir>/
  PROJECT.md    # durable context (what/why/how)
  todo.md       # current tasks (md checkboxes)
```

### `PROJECT.md` format

```markdown
---
name: bogdan-gavra
status: active        # active | paused | archived
tags: [business, campaigns]
updated: 2026-04-19
---

## What
One-line description of the project.

## Why
Goal and motivation. Why does this exist?

## How
Key commands, file paths, deploy instructions, dependencies.
```

### `todo.md` format

Plain markdown checkboxes. No frontmatter. Example:

```markdown
# Todo
- [ ] Draft catalog for Q2
- [x] Send Brevo campaign
- [ ] Follow up Jim Turnbull
```

### Project discovery

"Project" = any directory containing `PROJECT.md`. Explicit opt-in. No heuristic auto-detection at runtime (heuristics only used by `audit --suggest`).

## Components

### Single script: `D:\MEMORY\CODE\INFRA\MEM\mem.py`

**Modules (in-file, not separate):**
- `scan()` — walks `D:\MEMORY`, yields `(path, frontmatter, body)` tuples
- `parse_frontmatter(text)` — YAML frontmatter parser (no PyYAML dep; simple regex + manual parse)
- `format_ls(projects)` — table renderer for `mem ls`
- `format_tasks(todo_text)` — parse + highlight unchecked items
- `cmd_*(args)` — one function per subcommand

**Deps:** Python 3.12 stdlib only. No pip installs.

### Wrapper

`mem.bat` (Windows) / `mem` (bash alias) → invokes `python D:\MEMORY\CODE\INFRA\MEM\mem.py $@`.

Install path: `D:\MEMORY\CODE\INFRA\MEM\` (matches existing tentacle-style INFRA layout).

## CLI Commands

| Command | Behavior |
|---------|----------|
| `mem ls [--status X] [--tag Y]` | List projects: name, status, tags, updated. Optional filters. |
| `mem show <name>` | Print PROJECT.md to stdout. Exit 1 if not found. |
| `mem tasks [name]` | If name given: print todo.md. Else: print open items across all projects, grouped by project. |
| `mem active` | List projects with ≥1 unchecked todo item. |
| `mem search <query>` | Grep PROJECT.md + todo.md. Print matches with project name + line. |
| `mem new <name> [--path DIR]` | Scaffold PROJECT.md + todo.md stub. Defaults path to cwd. |
| `mem audit` | List dirs matching candidate heuristic (≥5 files, no PROJECT.md, under BUSINESS/CODE/DATA/PERSONAL). |
| `mem audit --suggest` | Same + print proposed stub for each. |
| `mem audit --fill` | Same + write stub PROJECT.md with placeholder content. |
| `mem edit <name>` | Open PROJECT.md in `$EDITOR` (fallback: `notepad`). |

## Data Flow

```
User: mem ls
  └─> scan(D:\MEMORY)
        └─> glob **/PROJECT.md (max depth 4, skip .git/.venv/node_modules)
        └─> for each: parse_frontmatter
  └─> filter by --status/--tag
  └─> format_ls -> stdout
```

```
User: mem audit --fill
  └─> walk D:\MEMORY (max depth 3)
  └─> collect dirs with ≥5 files and no PROJECT.md
  └─> for each: write stub PROJECT.md (status=paused, updated=today)
  └─> print count of files created
```

## Audit Heuristic

Candidate project dirs:
- Under `BUSINESS/`, `CODE/CAMPAIGNS/`, `CODE/INFRA/`, `DATA/`, `PERSONAL/`
- Has ≥5 files or ≥3 subdirs
- Not already has `PROJECT.md`
- Not excluded: `.git`, `.venv`, `node_modules`, `__pycache__`, `.vscode`, `.claude`, `.octogent`, `dist`, `build`

## Error Handling

- `mem show/edit/tasks <name>` with unknown name → print `project not found: <name>` to stderr, exit 1
- Malformed YAML frontmatter → print warning, skip project in `ls`, continue
- Missing `todo.md` when required → treat as empty (no error)
- Invalid `--status` / `--tag` values → print error, exit 2

## Testing

Test file: `D:\MEMORY\CODE\INFRA\MEM\test_mem.py` (unittest, stdlib)

Cases:
1. `scan` finds PROJECT.md in nested dirs
2. `parse_frontmatter` handles valid YAML, missing fields, malformed
3. `mem ls` filters by `--status active`
4. `mem show nonexistent` exits 1
5. `mem new foo` creates valid stub with today's date
6. `mem audit` skips excluded dirs (.git, .venv)
7. `mem tasks` parses `- [ ]` vs `- [x]` correctly
8. `mem search` returns matches with correct file + line

Test fixture: temp dir with 3 fake projects.

## Backfill Plan (after tool built)

1. `mem audit --suggest` → review candidate list (~30-50 dirs expected)
2. Remove false positives from list manually
3. `mem audit --fill` → write stubs
4. For high-priority projects (active business), `mem edit <name>` and fill in What/Why/How
5. Commit all new PROJECT.md files

Expected candidates:
- `BUSINESS/BOGDAN GAVRA`, `BUSINESS/JIM TURNBULL`, `BUSINESS/INTERJOB`, `BUSINESS/TUDOR SEICARESCU LIFE STRATEGY`
- `CODE/CAMPAIGNS/*` (each campaign subdir)
- `CODE/INFRA/*` (OCTOGENT, MEM, SKILLS, etc.)
- `DATA/EURES_LAPTOP`, `DATA/RO_DB`
- `PERSONAL/ASOC PROP`, `PERSONAL/CASABUZAU`

## Deferred / Future

If B proves insufficient later:
- Add tmux session layer (`mem work <name>`) — octogent's terminal concept
- Add `mem channel` for inter-project coordination notes
- Add JSON export for dashboard integration

Not building these now. YAGNI.

## Success Criteria

- `mem` runs in <500ms for `ls` across full tree
- All 30 octogent tentacles have matching PROJECT.md (source of truth unified)
- Can answer "what's active right now?" in one command
- Zero external dependencies
- Script < 300 lines
