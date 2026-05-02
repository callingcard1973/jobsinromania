#!/usr/bin/env python3
"""
Template Performance - Analyze which templates work best

Metrics per template:
- Total sends
- Reply rate
- Interest rate
- Unsubscribe rate
- Best performing subject lines

Usage:
    python3 template_performance.py                       # All campaigns
    python3 template_performance.py --campaign HORECA2026 # Single campaign
    python3 template_performance.py --days 30             # Last 30 days
    python3 template_performance.py --export              # Export report
    python3 template_performance.py --best                # Show best templates

Analyzes send logs and reply data.
"""

import os
import sys
import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
REPLIES_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/REPLIES")
CONVERSATIONS_DB = Path("/opt/ACTIVE/OPENDATA/DATA/CONVERSATIONS/conversations.json")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.template_perf_state.json")
LOGS_DIR = Path("/opt/ACTIVE/INFRA/LOGS/campaigns")


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_campaign_templates(campaign_name):
    """Get templates for campaign."""
    templates = {}
    template_dir = CAMPAIGNS_DIR / campaign_name / "templates"

    if not template_dir.exists():
        return templates

    for template_file in template_dir.glob("*.txt"):
        try:
            with open(template_file, 'r') as f:
                content = f.read()

            subject = ""
            for line in content.split('\n'):
                if line.startswith('Subject:'):
                    subject = line[8:].strip()
                    break

            templates[template_file.stem] = {
                'name': template_file.stem,
                'path': str(template_file),
                'subject': subject,
                'sends': 0,
                'replies': 0,
                'interested': 0,
                'unsubscribes': 0
            }
        except:
            pass

    return templates


def count_template_sends(campaign_name, template_name, days=30):
    """Count sends for specific template from logs."""
    count = 0

    for i in range(days):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        log_file = LOGS_DIR / f"{campaign_name}_{date_str}.log"

        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    # Count template usage
                    count += content.count(template_name)
            except:
                pass

    return count


def get_reply_stats_by_template():
    """Get reply statistics grouped by template (approximation)."""
    # This is an approximation since we may not track exact template per send
    stats = defaultdict(lambda: {'replies': 0, 'interested': 0, 'unsubscribes': 0})

    classified_file = REPLIES_DIR / "classified_replies.csv"
    if classified_file.exists():
        try:
            with open(classified_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    account = row.get('account', 'default')
                    category = row.get('category', '')

                    stats[account]['replies'] += 1
                    if category == 'INTERESTED':
                        stats[account]['interested'] += 1
                    elif category == 'UNSUBSCRIBE':
                        stats[account]['unsubscribes'] += 1
        except:
            pass

    return dict(stats)


def analyze_campaign(campaign_name, days=30):
    """Analyze template performance for campaign."""
    templates = get_campaign_templates(campaign_name)

    if not templates:
        log(f"No templates found for {campaign_name}")
        return []

    # Count sends per template (estimation based on log analysis)
    total_sends = 0
    for i in range(days):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        log_file = LOGS_DIR / f"{campaign_name}_{date_str}.log"

        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    content = f.read().lower()
                    sends_today = content.count('sent to') + content.count('success')
                    total_sends += sends_today
            except:
                pass

    # Distribute sends across templates (equal distribution if can't determine)
    if templates and total_sends > 0:
        per_template = total_sends // len(templates)
        for name in templates:
            templates[name]['sends'] = per_template

    # Get reply stats
    reply_stats = get_reply_stats_by_template()

    # Calculate metrics
    results = []
    for name, data in templates.items():
        sends = data['sends']
        replies = reply_stats.get(name, {}).get('replies', 0)
        interested = reply_stats.get(name, {}).get('interested', 0)
        unsubscribes = reply_stats.get(name, {}).get('unsubscribes', 0)

        results.append({
            'campaign': campaign_name,
            'template': name,
            'subject': data['subject'][:50],
            'sends': sends,
            'replies': replies,
            'interested': interested,
            'unsubscribes': unsubscribes,
            'reply_rate': round(replies / max(sends, 1) * 100, 2),
            'interest_rate': round(interested / max(sends, 1) * 100, 2),
            'unsub_rate': round(unsubscribes / max(sends, 1) * 100, 2),
            'score': 0
        })

    # Calculate score
    for r in results:
        r['score'] = min(100, int(
            r['interest_rate'] * 20 +
            r['reply_rate'] * 5 -
            r['unsub_rate'] * 10
        ))

    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def analyze_all_campaigns(days=30):
    """Analyze all campaigns."""
    all_results = []

    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if campaign_dir.is_dir():
            template_dir = campaign_dir / "templates"
            if template_dir.exists():
                results = analyze_campaign(campaign_dir.name, days)
                all_results.extend(results)

    # Sort by score
    all_results.sort(key=lambda x: x['score'], reverse=True)

    return all_results


def print_results(results, limit=20):
    """Print formatted results."""
    print("\n" + "="*70)
    print("TEMPLATE PERFORMANCE REPORT")
    print("="*70)

    for r in results[:limit]:
        indicator = "🟢" if r['score'] >= 50 else "🟡" if r['score'] >= 25 else "🔴"
        print(f"\n{indicator} {r['campaign']} / {r['template']} (score: {r['score']})")
        print(f"  Subject: {r['subject']}")
        print(f"  Sends: {r['sends']} | Replies: {r['replies']} ({r['reply_rate']}%)")
        print(f"  Interested: {r['interested']} | Unsubs: {r['unsubscribes']}")

    print("\n" + "="*70)


def show_best_templates(results, top=5):
    """Show best performing templates."""
    print("\n🏆 TOP PERFORMING TEMPLATES\n")

    for i, r in enumerate(results[:top], 1):
        print(f"{i}. {r['campaign']} / {r['template']}")
        print(f"   Score: {r['score']} | Interest: {r['interest_rate']}%")
        print(f"   Subject: {r['subject']}")
        print()


def export_results(results, output_file=None):
    """Export results to CSV."""
    output_file = output_file or Path("/opt/ACTIVE/OPENDATA/DATA/template_performance.csv")

    fieldnames = ['campaign', 'template', 'subject', 'sends', 'replies',
                  'interested', 'unsubscribes', 'reply_rate', 'interest_rate', 'score']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    log(f"Exported to {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Template Performance")
    parser.add_argument("--campaign", help="Single campaign to analyze")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--best", action="store_true", help="Show best templates")
    parser.add_argument("--limit", type=int, default=20, help="Results limit")

    args = parser.parse_args()

    if args.campaign:
        results = analyze_campaign(args.campaign, args.days)
    else:
        results = analyze_all_campaigns(args.days)

    if args.best:
        show_best_templates(results)
    else:
        print_results(results, args.limit)

    if args.export:
        export_results(results)


if __name__ == "__main__":
    main()
