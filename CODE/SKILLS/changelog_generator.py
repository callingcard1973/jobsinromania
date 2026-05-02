#!/usr/bin/env python3
"""
Changelog Generator - Create changelogs from git commits
Usage: python3 changelog_generator.py [path] [--since date] [--output CHANGELOG.md]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# ============================================================
# COMMIT CATEGORIES
# ============================================================

CATEGORIES = {
    'feat': ('Features', ['feat', 'feature', 'add', 'new']),
    'fix': ('Bug Fixes', ['fix', 'bug', 'patch', 'resolve']),
    'perf': ('Performance', ['perf', 'performance', 'optimize', 'speed']),
    'refactor': ('Refactoring', ['refactor', 'restructure', 'reorganize']),
    'docs': ('Documentation', ['docs', 'doc', 'readme', 'comment']),
    'test': ('Tests', ['test', 'testing', 'spec']),
    'chore': ('Maintenance', ['chore', 'update', 'upgrade', 'bump']),
    'style': ('Styling', ['style', 'format', 'lint']),
    'ci': ('CI/CD', ['ci', 'cd', 'pipeline', 'deploy']),
    'security': ('Security', ['security', 'vuln', 'cve']),
}

def categorize_commit(message: str) -> str:
    """Categorize commit based on message"""
    msg_lower = message.lower()

    # Check conventional commit format first
    conv_match = re.match(r'^(\w+)(?:\(.+\))?:', msg_lower)
    if conv_match:
        prefix = conv_match.group(1)
        for cat, (_, keywords) in CATEGORIES.items():
            if prefix in keywords:
                return cat

    # Check keywords
    for cat, (_, keywords) in CATEGORIES.items():
        for kw in keywords:
            if kw in msg_lower:
                return cat

    return 'other'

# ============================================================
# GIT OPERATIONS
# ============================================================

def get_git_log(path: str, since: str = None, until: str = None) -> List[Dict]:
    """Get git log entries"""
    cmd = ['git', '-C', path, 'log', '--pretty=format:%H|%an|%ae|%ad|%s', '--date=short']

    if since:
        cmd.append(f'--since={since}')
    if until:
        cmd.append(f'--until={until}')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        commits = []

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|', 4)
            if len(parts) >= 5:
                commits.append({
                    'hash': parts[0][:8],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'message': parts[4],
                    'category': categorize_commit(parts[4]),
                })

        return commits
    except Exception as e:
        return []

def get_tags(path: str) -> List[Dict]:
    """Get git tags with dates"""
    cmd = ['git', '-C', path, 'tag', '-l', '--sort=-creatordate', '--format=%(refname:short)|%(creatordate:short)']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        tags = []

        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                name, date = line.split('|', 1)
                tags.append({'name': name, 'date': date})

        return tags
    except Exception:
        return []

def get_repo_info(path: str) -> Dict:
    """Get repository info"""
    info = {'name': Path(path).name, 'branch': '', 'remote': ''}

    try:
        result = subprocess.run(['git', '-C', path, 'rev-parse', '--abbrev-ref', 'HEAD'],
                              capture_output=True, text=True, timeout=5)
        info['branch'] = result.stdout.strip()

        result = subprocess.run(['git', '-C', path, 'remote', 'get-url', 'origin'],
                              capture_output=True, text=True, timeout=5)
        info['remote'] = result.stdout.strip()
    except Exception:
        pass

    return info

# ============================================================
# CHANGELOG GENERATION
# ============================================================

def generate_changelog(commits: List[Dict], repo_info: Dict = None, format: str = 'md') -> str:
    """Generate changelog from commits"""

    # Group by category
    by_category = defaultdict(list)
    for commit in commits:
        by_category[commit['category']].append(commit)

    # Group by date
    by_date = defaultdict(list)
    for commit in commits:
        by_date[commit['date']].append(commit)

    if format == 'md':
        return generate_markdown(by_category, by_date, repo_info)
    else:
        return generate_text(by_category, by_date, repo_info)

def generate_markdown(by_category: Dict, by_date: Dict, repo_info: Dict) -> str:
    """Generate Markdown changelog"""
    lines = [
        "# Changelog",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]

    if repo_info:
        lines.append(f"Repository: {repo_info.get('name', 'Unknown')}")
        if repo_info.get('branch'):
            lines.append(f"Branch: {repo_info['branch']}")

    lines.extend(["", "---", ""])

    # By category
    lines.append("## Changes by Category")
    lines.append("")

    for cat, (title, _) in CATEGORIES.items():
        commits = by_category.get(cat, [])
        if commits:
            lines.append(f"### {title}")
            lines.append("")
            for c in commits:
                lines.append(f"- {c['message']} (`{c['hash']}` by {c['author']})")
            lines.append("")

    # Other commits
    other = by_category.get('other', [])
    if other:
        lines.append("### Other")
        lines.append("")
        for c in other:
            lines.append(f"- {c['message']} (`{c['hash']}`)")
        lines.append("")

    # Timeline
    lines.extend(["---", "", "## Timeline", ""])

    for date in sorted(by_date.keys(), reverse=True):
        commits = by_date[date]
        lines.append(f"### {date}")
        lines.append("")
        for c in commits:
            cat_name = CATEGORIES.get(c['category'], ('Other', []))[0]
            lines.append(f"- **[{cat_name}]** {c['message']}")
        lines.append("")

    return '\n'.join(lines)

def generate_text(by_category: Dict, by_date: Dict, repo_info: Dict) -> str:
    """Generate plain text changelog"""
    lines = [
        "=" * 60,
        "CHANGELOG",
        "=" * 60,
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ]

    if repo_info:
        lines.append(f"Repository: {repo_info.get('name', 'Unknown')}")

    lines.extend(["", "-" * 60, ""])

    total = sum(len(v) for v in by_category.values())
    lines.append(f"Total commits: {total}")
    lines.append("")

    for cat, (title, _) in CATEGORIES.items():
        commits = by_category.get(cat, [])
        if commits:
            lines.append(f"{title}: {len(commits)}")

    lines.extend(["", "=" * 60, "DETAILS", "=" * 60, ""])

    for cat, (title, _) in CATEGORIES.items():
        commits = by_category.get(cat, [])
        if commits:
            lines.append(f"\n{title.upper()}")
            lines.append("-" * 40)
            for c in commits:
                lines.append(f"  [{c['date']}] {c['message']}")

    return '\n'.join(lines)

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if '-h' in args or '--help' in args:
        print(f"""
{'='*60}
CHANGELOG GENERATOR
{'='*60}

Usage: changelog_generator.py [path] [options]

Options:
  --since DATE      Start date (YYYY-MM-DD or "1 week ago")
  --until DATE      End date
  --output FILE     Save to file (default: print)
  --format FORMAT   md or txt (default: md)
  --days N          Last N days (shortcut for --since)

Examples:
  changelog_generator.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY
  changelog_generator.py . --since "2025-01-01" --output CHANGELOG.md
  changelog_generator.py --days 30
  changelog_generator.py /path/to/repo --format txt
""")
        return

    # Parse arguments
    path = '.'
    since = until = output_file = None
    format = 'md'

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == '--since' and i + 1 < len(args):
            since = args[i + 1]
            i += 2
        elif arg == '--until' and i + 1 < len(args):
            until = args[i + 1]
            i += 2
        elif arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif arg == '--format' and i + 1 < len(args):
            format = args[i + 1]
            i += 2
        elif arg == '--days' and i + 1 < len(args):
            days = int(args[i + 1])
            since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            i += 2
        elif not arg.startswith('-') and os.path.isdir(arg):
            path = arg
            i += 1
        else:
            i += 1

    print(f"\n{'='*60}")
    print("CHANGELOG GENERATOR")
    print(f"{'='*60}\n")

    repo_info = get_repo_info(path)
    print(f"Repository: {repo_info.get('name', path)}")
    print(f"Branch: {repo_info.get('branch', 'unknown')}")

    if since:
        print(f"Since: {since}")

    commits = get_git_log(path, since, until)
    print(f"Commits found: {len(commits)}")

    if not commits:
        print("\nNo commits found in the specified range")
        return

    changelog = generate_changelog(commits, repo_info, format)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(changelog)
        print(f"\nSaved to: {output_file}")
    else:
        print(f"\n{changelog[:3000]}")
        if len(changelog) > 3000:
            print(f"\n... ({len(changelog)} chars, use --output to save)")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
