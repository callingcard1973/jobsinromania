#!/usr/bin/env python3
"""
CLAUDE.md Linter - Measures token consumption across all CLAUDE.md files.
Identifies bloat, flags large files, and provides before/after metrics.

Usage:
  python claude_md_lint.py              # Scan all CLAUDE.md files
  python claude_md_lint.py --summary    # Show only top-level summary
  python claude_md_lint.py --export     # Export results to JSON
"""

import os
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Rough approximation: 1 token ≈ 4 chars (Claude token estimation)
CHARS_PER_TOKEN = 4

def estimate_tokens(text):
    """Rough token estimate: chars / 4"""
    return len(text) // CHARS_PER_TOKEN

def analyze_markdown_file(filepath):
    """Analyze a single CLAUDE.md file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return None

    lines = content.split('\n')
    tokens = estimate_tokens(content)

    # Parse sections
    sections = defaultdict(list)
    current_section = "intro"

    for i, line in enumerate(lines):
        if line.startswith('##'):
            current_section = line.strip('# ').lower()
        sections[current_section].append((i + 1, line))

    return {
        'filepath': str(filepath),
        'lines': len(lines),
        'tokens': tokens,
        'chars': len(content),
        'sections': {k: len(v) for k, v in sections.items()},
        'section_tokens': {k: estimate_tokens('\n'.join([line for _, line in v]))
                          for k, v in sections.items()},
        'content': content
    }

def find_all_claude_md(root_dir):
    """Recursively find all CLAUDE.md files."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'CLAUDE.md' in filenames:
            filepath = Path(dirpath) / 'CLAUDE.md'
            results.append(filepath)
    return sorted(results)

def report_bloat(analysis, threshold_lines=50, threshold_tokens=1500):
    """Identify sections that exceed thresholds."""
    bloat = []
    for section, tokens in analysis['section_tokens'].items():
        lines = analysis['sections'][section]
        if tokens > 300 or lines > 15:  # Section-level thresholds
            bloat.append({
                'section': section,
                'lines': lines,
                'tokens': tokens,
                'pct_of_file': round(100 * tokens / analysis['tokens'], 1)
            })
    return sorted(bloat, key=lambda x: x['tokens'], reverse=True)

def main():
    parser = argparse.ArgumentParser(description='Analyze CLAUDE.md token consumption')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    parser.add_argument('--export', action='store_true', help='Export to JSON')
    parser.add_argument('--root', default='D:\\MEMORY', help='Root directory to scan')
    args = parser.parse_args()

    print(f"Scanning {args.root} for CLAUDE.md files...\n")

    files = find_all_claude_md(args.root)
    analyses = []
    total_tokens = 0
    total_lines = 0
    flagged_files = []

    for filepath in files:
        analysis = analyze_markdown_file(filepath)
        if analysis:
            analyses.append(analysis)
            total_tokens += analysis['tokens']
            total_lines += analysis['lines']

            # Flag if exceeds thresholds
            if analysis['lines'] > 50 or analysis['tokens'] > 1500:
                flagged_files.append(analysis)

    # Summary
    print(f"{'File':<50} {'Lines':<8} {'Tokens':<10} {'Status'}")
    print("-" * 80)

    for analysis in sorted(analyses, key=lambda a: a['tokens'], reverse=True):
        short_path = analysis['filepath'].replace('D:\\MEMORY\\', '')
        status = "[BLOAT]" if analysis['tokens'] > 1500 else "[OK]"
        print(f"{short_path:<50} {analysis['lines']:<8} {analysis['tokens']:<10} {status}")

    print("-" * 80)
    print(f"{'TOTAL':<50} {total_lines:<8} {total_tokens:<10}")
    print()

    if not args.summary:
        print("\n=== BLOAT BREAKDOWN ===\n")
        for analysis in flagged_files:
            print(f"\n{analysis['filepath']}")
            print(f"   {analysis['lines']} lines | {analysis['tokens']} tokens")
            bloat = report_bloat(analysis)
            if bloat:
                print(f"   Top sections by token cost:")
                for item in bloat[:5]:
                    print(f"      - {item['section']:<20} {item['tokens']:>5} tokens ({item['pct_of_file']:>4}%)")

    print(f"\n[TARGET] <= 50 lines, <= 1,500 tokens per CLAUDE.md file")
    print(f"   Current average: {total_lines // len(analyses) if analyses else 0} lines, "
          f"{total_tokens // len(analyses) if analyses else 0} tokens")

    if args.export:
        export_data = {
            'scan_root': args.root,
            'files': analyses,
            'totals': {'files': len(analyses), 'lines': total_lines, 'tokens': total_tokens},
            'flagged': len(flagged_files)
        }
        output_file = 'D:\\MEMORY\\OPTIMIZE TOKENS\\lint_report.json'
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"\n[EXPORTED] Report saved to {output_file}")

if __name__ == '__main__':
    main()
