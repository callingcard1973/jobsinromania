#!/usr/bin/env python3
"""Validate .claude harnesses: agent frontmatter, unique names, valid model, skill triggers."""
import sys
from pathlib import Path

import yaml

REQUIRED_AGENT_KEYS = {"name", "description", "model", "tools"}
VALID_MODELS = {"opus", "sonnet", "haiku", "fable",
                "claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"}
TRIGGER_HINTS = ("use when", "triggers", "use this", "auto-applies", "used when")


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        return {"_yaml_error": str(e)}


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    agents = list(root.rglob(".claude/agents/*.md"))
    skills = list(root.rglob(".claude/skills/**/SKILL.md"))
    print(f"Scanning {len(agents)} agents, {len(skills)} skills under {root}\n")

    issues = []
    names = {}
    for a in agents:
        fm = parse_frontmatter(a)
        if fm is None:
            issues.append(f"NO FRONTMATTER: {a}")
            continue
        if "_yaml_error" in fm:
            issues.append(f"BAD YAML: {a}: {fm['_yaml_error']}")
            continue
        missing = REQUIRED_AGENT_KEYS - set(fm)
        if missing:
            issues.append(f"MISSING KEYS {sorted(missing)}: {a}")
        model = str(fm.get("model", "")).strip()
        if model and model not in VALID_MODELS:
            issues.append(f"UNKNOWN MODEL '{model}': {a}")
        name = fm.get("name")
        if name:
            names.setdefault(name, []).append(a)

    for name, paths in names.items():
        if len(paths) > 1:
            issues.append(f"DUPLICATE NAME '{name}': " + ", ".join(str(p) for p in paths))

    for s in skills:
        fm = parse_frontmatter(s)
        if not fm or "_yaml_error" in (fm or {}):
            issues.append(f"SKILL BAD/NO FRONTMATTER: {s}")
            continue
        desc = str(fm.get("description", "")).lower()
        if not desc:
            issues.append(f"SKILL NO DESCRIPTION: {s}")
        elif not any(h in desc for h in TRIGGER_HINTS):
            issues.append(f"SKILL NO TRIGGER PHRASE: {s}")

    for i in issues:
        print(f"  {i}")
    print(f"\nRESULT: {'FAIL' if issues else 'PASS'} ({len(issues)} issues)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
