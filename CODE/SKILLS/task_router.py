#!/usr/bin/env python3
"""Task Router - Detects task type and routes to appropriate context modules."""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional

TASK_PATTERNS: Dict[str, List[str]] = {
    "scraper": [
        r"scrap(e|er|ing)",
        r"playwright|httpx|cloudscraper|requests",
        r"/opt/ACTIVE/SCRAPERS/EUROPE/",
        r"job.*(portal|board|site)",
        r"crawl|harvest|extract",
        r"selenium|browser"
    ],
    "csv": [
        r"\.csv\b",
        r"analyz|analis|dedupe|column|row",
        r"contacts?|leads?|emails?",
        r"dataframe|pandas",
        r"export|import.*data"
    ],
    "email": [
        r"brevo|smtp|campaign",
        r"send.*(email|mail)",
        r"bounce|deliver",
        r"newsletter|template",
        r"domain.*auth|dkim|spf"
    ],
    "debug": [
        r"error|fail(ed|ing)?|broken|fix|bug",
        r"not.*(work|run|load)",
        r"traceback|exception",
        r"debug|diagnose|troubleshoot",
        r"why.*(fail|error|crash)"
    ],
    "ops": [
        r"sync|backup|restore",
        r"raspi|health|monitor",
        r"cron|schedule",
        r"disk|memory|cpu",
        r"deploy|maintain"
    ]
}

MODULE_MAP: Dict[str, List[str]] = {
    "scraper": ["scraper.md", "skills.md"],
    "csv": ["csv.md", "skills.md"],
    "email": ["email.md"],
    "debug": ["scraper.md", "skills.md"],
    "ops": ["ops.md"],
    "general": []  # Core only
}


def detect_task(user_message: str, cwd: Optional[str] = None) -> str:
    """
    Detect task type from message + context.

    Args:
        user_message: The user's input message
        cwd: Current working directory (defaults to os.getcwd())

    Returns:
        Task type string: scraper, csv, email, debug, ops, or general
    """
    msg_lower = user_message.lower()
    cwd = cwd or os.getcwd()

    scores: Dict[str, int] = {task: 0 for task in TASK_PATTERNS}

    # Score by message patterns
    for task, patterns in TASK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                scores[task] += 2

    # Score by current directory
    if "SCRAPERS" in cwd:
        scores["scraper"] += 3
    elif "EMAIL" in cwd:
        scores["email"] += 3
    elif "SKILLS" in cwd:
        scores["ops"] += 1

    # Score by files in current directory (only if no message patterns matched)
    max_msg_score = max(scores.values())
    if max_msg_score == 0:
        try:
            cwd_path = Path(cwd)
            if list(cwd_path.glob("*.csv")):
                scores["csv"] += 1
            if list(cwd_path.glob("*scraper*.py")) or list(cwd_path.glob("*crawler*.py")):
                scores["scraper"] += 1
        except (OSError, PermissionError):
            pass

    # Get best match
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def get_context_modules(task_type: str) -> List[str]:
    """
    Return which CLAUDE.md modules to load for given task type.

    Args:
        task_type: One of scraper, csv, email, debug, ops, general

    Returns:
        List of module filenames to load from ~/.claude/rules/
    """
    return MODULE_MAP.get(task_type, [])


def get_module_paths(task_type: str, rules_dir: str = None) -> List[Path]:
    """
    Get full paths to context modules.

    Args:
        task_type: Task type string
        rules_dir: Path to rules directory (default: ~/.claude/rules)

    Returns:
        List of Path objects for existing module files
    """
    if rules_dir is None:
        rules_dir = Path.home() / ".claude" / "rules"
    else:
        rules_dir = Path(rules_dir)

    modules = get_context_modules(task_type)
    paths = []

    for module in modules:
        module_path = rules_dir / module
        if module_path.exists():
            paths.append(module_path)

    return paths


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        task = detect_task(message)
        modules = get_context_modules(task)
        print(f"Task: {task}")
        print(f"Modules: {', '.join(modules) if modules else 'core only'}")
    else:
        # Demo
        examples = [
            "fix the norway scraper, it's broken",
            "analyze the contacts.csv file",
            "send campaign to buildjobs.eu list",
            "sync data to raspi",
            "what time is it"
        ]
        for msg in examples:
            task = detect_task(msg)
            modules = get_context_modules(task)
            print(f"'{msg[:40]}...' -> {task} [{', '.join(modules) or 'core'}]")
