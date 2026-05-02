#!/usr/bin/env python3
"""
Internal Comms - Generate newsletters, status reports, campaign emails
Usage: python3 internal_comms.py [newsletter|status|campaign|faq] [options]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================
# TEMPLATES
# ============================================================

NEWSLETTER_TEMPLATE = """
================================================================================
{company} - {title}
{date}
================================================================================

{greeting}

{intro}

{sections}

{closing}

{signature}
================================================================================
"""

STATUS_TEMPLATE = """
================================================================================
STATUS REPORT - {period}
Generated: {date}
================================================================================

EXECUTIVE SUMMARY
-----------------
{summary}

KEY METRICS
-----------
{metrics}

ACCOMPLISHMENTS
---------------
{accomplishments}

CHALLENGES
----------
{challenges}

NEXT STEPS
----------
{next_steps}

================================================================================
"""

CAMPAIGN_EMAIL_TEMPLATE = """
Subject: {subject}

{greeting}

{body}

{cta}

{closing}

{signature}

---
{footer}
"""

FAQ_TEMPLATE = """
================================================================================
FREQUENTLY ASKED QUESTIONS
{topic}
================================================================================

{questions}

================================================================================
Last updated: {date}
"""

# ============================================================
# CONTENT GENERATORS
# ============================================================

GREETINGS = {
    'formal': ['Dear Team,', 'Dear Colleagues,', 'Dear Partners,'],
    'casual': ['Hi everyone!', 'Hello team!', 'Hey all,'],
    'professional': ['Good morning,', 'Greetings,', 'Hello,'],
}

CLOSINGS = {
    'formal': ['Best regards,', 'Sincerely,', 'Kind regards,'],
    'casual': ['Cheers,', 'Thanks!', 'All the best,'],
    'professional': ['Best,', 'Regards,', 'Thank you,'],
}

def generate_newsletter(
    title: str,
    sections: List[Dict],
    company: str = "InterjobRO",
    tone: str = "professional",
    intro: str = None,
) -> str:
    """Generate a newsletter"""

    greeting = GREETINGS.get(tone, GREETINGS['professional'])[0]
    closing = CLOSINGS.get(tone, CLOSINGS['professional'])[0]

    if not intro:
        intro = f"Welcome to this edition of our newsletter. Here's what's new:"

    sections_text = ""
    for i, section in enumerate(sections, 1):
        sections_text += f"\n{i}. {section.get('title', 'Update')}\n"
        sections_text += "-" * 40 + "\n"
        sections_text += section.get('content', '') + "\n"

    return NEWSLETTER_TEMPLATE.format(
        company=company,
        title=title,
        date=datetime.now().strftime('%B %d, %Y'),
        greeting=greeting,
        intro=intro,
        sections=sections_text,
        closing=closing,
        signature=f"\nThe {company} Team",
    )

def generate_status_report(
    period: str,
    summary: str,
    metrics: Dict,
    accomplishments: List[str],
    challenges: List[str],
    next_steps: List[str],
) -> str:
    """Generate a status report"""

    metrics_text = ""
    for key, value in metrics.items():
        metrics_text += f"  - {key}: {value}\n"

    accomplishments_text = "\n".join(f"  * {a}" for a in accomplishments)
    challenges_text = "\n".join(f"  * {c}" for c in challenges)
    next_steps_text = "\n".join(f"  * {n}" for n in next_steps)

    return STATUS_TEMPLATE.format(
        period=period,
        date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        summary=summary,
        metrics=metrics_text,
        accomplishments=accomplishments_text,
        challenges=challenges_text,
        next_steps=next_steps_text,
    )

def generate_campaign_email(
    subject: str,
    body: str,
    cta: str = None,
    tone: str = "professional",
    sender: str = "InterjobRO",
    footer: str = None,
) -> str:
    """Generate a campaign email"""

    greeting = GREETINGS.get(tone, GREETINGS['professional'])[0]
    closing = CLOSINGS.get(tone, CLOSINGS['professional'])[0]

    if not cta:
        cta = ""
    else:
        cta = f"\n{cta}\n"

    if not footer:
        footer = f"Sent by {sender} | Unsubscribe: reply with STOP"

    return CAMPAIGN_EMAIL_TEMPLATE.format(
        subject=subject,
        greeting=greeting,
        body=body,
        cta=cta,
        closing=closing,
        signature=f"\n{sender}",
        footer=footer,
    )

def generate_faq(
    topic: str,
    questions: List[Dict],
) -> str:
    """Generate FAQ document"""

    questions_text = ""
    for i, qa in enumerate(questions, 1):
        questions_text += f"\nQ{i}: {qa.get('question', '')}\n"
        questions_text += f"A{i}: {qa.get('answer', '')}\n"
        questions_text += "-" * 40 + "\n"

    return FAQ_TEMPLATE.format(
        topic=f"- {topic}" if topic else "",
        questions=questions_text,
        date=datetime.now().strftime('%Y-%m-%d'),
    )

# ============================================================
# SCRAPER STATUS INTEGRATION
# ============================================================

def get_scraper_metrics() -> Dict:
    """Get metrics from scraper_monitor if available"""
    try:
        import subprocess
        result = subprocess.run(
            ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/scraper_monitor.py', '--json'],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(result.stdout)

        healthy = sum(1 for s in data if s.get('health') == 'healthy')
        total = len(data)
        total_rows = sum(s.get('last_output_rows', 0) for s in data)

        return {
            'Scrapers Active': f"{healthy}/{total}",
            'Total Rows (latest)': total_rows,
            'Last Check': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
    except Exception:
        return {}

def get_contact_metrics() -> Dict:
    """Get metrics from master_contacts if available"""
    try:
        import subprocess
        result = subprocess.run(
            ['/opt/ACTIVE/INFRA/venv/bin/python3', '/opt/ACTIVE/INFRA/SKILLS/master_contacts.py'],
            capture_output=True, text=True, timeout=120
        )
        # Parse output for key metrics
        output = result.stdout
        metrics = {}

        for line in output.split('\n'):
            if 'Total emails:' in line:
                metrics['Total Emails'] = line.split(':')[1].strip()
            elif 'Unique:' in line:
                metrics['Unique Emails'] = line.split(':')[1].strip()
            elif 'Corporate:' in line:
                metrics['Corporate'] = line.split(':')[1].strip()

        return metrics
    except Exception:
        return {}

def generate_weekly_newsletter() -> str:
    """Generate automated weekly newsletter with real data"""

    scraper_metrics = get_scraper_metrics()
    contact_metrics = get_contact_metrics()

    sections = []

    if scraper_metrics:
        sections.append({
            'title': 'Scraper Status',
            'content': '\n'.join(f"  {k}: {v}" for k, v in scraper_metrics.items()),
        })

    if contact_metrics:
        sections.append({
            'title': 'Contact Database',
            'content': '\n'.join(f"  {k}: {v}" for k, v in contact_metrics.items()),
        })

    sections.append({
        'title': 'Coming Up',
        'content': '  - Continued scraping operations\n  - Database maintenance\n  - Quality checks',
    })

    return generate_newsletter(
        title="Weekly Operations Update",
        sections=sections,
        intro="Here's your weekly summary of scraping operations and contact database status.",
    )

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
INTERNAL COMMS - Content Generator
{'='*60}

Usage: internal_comms.py <type> [options]

Types:
  newsletter    Generate a newsletter
  status        Generate a status report
  campaign      Generate a campaign email
  faq           Generate FAQ document
  weekly        Auto-generate weekly newsletter with real data

Options:
  --title TEXT      Title/subject
  --tone TONE       formal, casual, professional (default)
  --output FILE     Save to file
  --json            Input sections as JSON

Examples:
  internal_comms.py weekly
  internal_comms.py newsletter --title "March Update"
  internal_comms.py campaign --title "New Jobs Available" --tone casual
  internal_comms.py status --output /tmp/status.txt
""")
        return

    doc_type = args[0]
    title = "Update"
    tone = "professional"
    output_file = None

    for i, arg in enumerate(args):
        if arg == '--title' and i + 1 < len(args):
            title = args[i + 1]
        elif arg == '--tone' and i + 1 < len(args):
            tone = args[i + 1]
        elif arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]

    print(f"\n{'='*60}")
    print(f"INTERNAL COMMS - {doc_type.upper()}")
    print(f"{'='*60}\n")

    content = ""

    if doc_type == 'weekly':
        content = generate_weekly_newsletter()

    elif doc_type == 'newsletter':
        content = generate_newsletter(
            title=title,
            sections=[
                {'title': 'Section 1', 'content': 'Add your content here...'},
                {'title': 'Section 2', 'content': 'Add your content here...'},
            ],
            tone=tone,
        )

    elif doc_type == 'status':
        content = generate_status_report(
            period=f"Week of {datetime.now().strftime('%B %d, %Y')}",
            summary="Summary of activities for this period.",
            metrics={'Metric 1': 'Value 1', 'Metric 2': 'Value 2'},
            accomplishments=['Accomplishment 1', 'Accomplishment 2'],
            challenges=['Challenge 1'],
            next_steps=['Next step 1', 'Next step 2'],
        )

    elif doc_type == 'campaign':
        content = generate_campaign_email(
            subject=title,
            body="Your campaign message here.\n\nExplain your offer or announcement.",
            cta="Click here to learn more: [LINK]",
            tone=tone,
        )

    elif doc_type == 'faq':
        content = generate_faq(
            topic=title,
            questions=[
                {'question': 'Question 1?', 'answer': 'Answer 1'},
                {'question': 'Question 2?', 'answer': 'Answer 2'},
            ],
        )

    else:
        print(f"Unknown type: {doc_type}")
        return

    if output_file:
        with open(output_file, 'w') as f:
            f.write(content)
        print(f"Saved to: {output_file}")
    else:
        print(content)

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
