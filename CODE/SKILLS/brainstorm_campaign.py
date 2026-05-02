#!/usr/bin/env python3
"""
Campaign Planning Brainstorming - Design email campaigns
Usage: python3 brainstorm_campaign.py [--interactive] [--name NAME]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path

DOCS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/campaigns/plans')
TEMPLATES_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/templates')
CONTACTS_DIR = Path('/mnt/hdd/SCRAPER_DATA/csv')

QUESTIONS = {
    'goal': {
        'q': 'What is the campaign goal?',
        'opts': ['Job candidate recruitment', 'Employer outreach', 'Partnership inquiry', 'Service promotion', 'Follow-up/nurture']
    },
    'audience': {
        'q': 'Who is the target audience?',
        'opts': ['Job seekers (workers)', 'Employers/HR', 'Recruitment agencies', 'Mixed audience', 'Specific company list']
    },
    'region': {
        'q': 'Geographic target?',
        'opts': ['Nordic countries', 'Poland', 'Romania', 'All Europe', 'Specific country']
    },
    'email_type': {
        'q': 'What type of emails?',
        'opts': ['Corporate emails only', 'All emails', 'Verified emails only', 'New contacts only']
    },
    'volume': {
        'q': 'Campaign size?',
        'opts': ['Small test (50-100)', 'Medium (500-1000)', 'Large (2000-5000)', 'Full list']
    },
    'template': {
        'q': 'Email template style?',
        'opts': ['Professional/formal', 'Friendly/casual', 'Brief/direct', 'Detailed with benefits', 'Custom template']
    },
    'schedule': {
        'q': 'Sending schedule?',
        'opts': ['Immediate (today)', 'Tomorrow morning', 'Spread over 3 days', 'Spread over week', 'Manual trigger']
    },
    'follow_up': {
        'q': 'Follow-up plan?',
        'opts': ['No follow-up', 'Single follow-up after 3 days', 'Two follow-ups', 'Depends on response']
    }
}

def get_available_contacts():
    """List available contact files"""
    files = []
    if CONTACTS_DIR.exists():
        for f in CONTACTS_DIR.glob('*.csv'):
            size = f.stat().st_size // 1024
            files.append((f.name, size))
    return sorted(files, key=lambda x: -x[1])[:15]

def get_brevo_limits():
    """Get current Brevo sending limits"""
    return {
        'buildjobs.eu': 290,
        'factoryjobs.eu': 290,
        'careworkers.eu': 290,
        'mivromania.info': 290,
        'mivromania.online': 290,
        'cifn.info': 290,
        'interjob.ro': 290,
        'nepalezi.com': 290,
        'TOTAL': 2320
    }

def interactive_session():
    """Run interactive Q&A session"""
    print(f"\n{'='*60}")
    print("CAMPAIGN PLANNING BRAINSTORMING")
    print(f"{'='*60}\n")

    # Show available resources
    contacts = get_available_contacts()
    limits = get_brevo_limits()

    print("AVAILABLE CONTACT FILES:")
    for name, size in contacts[:10]:
        print(f"  {name} ({size}KB)")

    print(f"\nBREVO DAILY LIMIT: {limits['TOTAL']}/day across {len(limits)-1} domains\n")

    answers = {}

    for key, item in QUESTIONS.items():
        print(f"\n{item['q']}")
        for i, opt in enumerate(item['opts'], 1):
            print(f"  {i}. {opt}")

        while True:
            try:
                choice = input(f"\nChoice [1-{len(item['opts'])}]: ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(item['opts']):
                    answers[key] = item['opts'][int(choice)-1]
                    break
                elif choice:
                    answers[key] = choice
                    break
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return None

    # Additional details
    print("\nAdditional details:")
    answers['campaign_name'] = input("Campaign name: ").strip() or f"campaign_{datetime.now().strftime('%Y%m%d')}"
    answers['subject_line'] = input("Email subject line: ").strip() or "TBD"
    answers['sender_domain'] = input(f"Sender domain [{', '.join(list(limits.keys())[:3])}...]: ").strip() or "interjob.ro"

    return answers

def generate_campaign_plan(answers, name=None):
    """Generate campaign plan from answers"""
    date = datetime.now().strftime('%Y-%m-%d')
    campaign_name = name or answers.get('campaign_name', 'campaign')

    # Calculate send schedule
    schedule = calculate_schedule(answers)

    # Determine contact selection
    contact_criteria = determine_contacts(answers)

    plan = f"""# Campaign Plan: {campaign_name}
Generated: {date}

## Campaign Overview
- **Goal**: {answers.get('goal', 'TBD')}
- **Target Audience**: {answers.get('audience', 'TBD')}
- **Region**: {answers.get('region', 'TBD')}
- **Subject Line**: {answers.get('subject_line', 'TBD')}

## Contact Selection

### Criteria
{contact_criteria}

### Email Type Filter
{answers.get('email_type', 'All emails')}

### Expected Volume
{answers.get('volume', 'TBD')}

## Sending Configuration

### Sender Domain
{answers.get('sender_domain', 'interjob.ro')}

### Schedule
{schedule}

### Brevo Limits
- Daily limit per domain: 290
- Total daily capacity: 2,320
- Recommended: Stay under 80% (1,850/day)

## Template

### Style
{answers.get('template', 'Professional/formal')}

### Structure
1. Greeting (personalized if name available)
2. Value proposition (1-2 sentences)
3. Call to action
4. Contact info (www.interjob.ro, office@interjob.ro)
5. Unsubscribe link

## Follow-up Plan
{answers.get('follow_up', 'No follow-up')}

## Success Metrics

### Track
- [ ] Open rate (target: >20%)
- [ ] Click rate (target: >3%)
- [ ] Reply rate (target: >1%)
- [ ] Bounce rate (target: <5%)
- [ ] Unsubscribe rate (target: <1%)

### Warning Thresholds
- Bounce rate >10%: Pause and clean list
- Unsubscribe >2%: Review targeting
- Spam complaints: Stop immediately

## Pre-Launch Checklist

- [ ] Contact list cleaned and deduplicated
- [ ] Email template created and tested
- [ ] Subject line A/B test (if >1000 contacts)
- [ ] Sender domain authenticated (Brevo)
- [ ] Unsubscribe link working
- [ ] Test send to office@interjob.ro
- [ ] Schedule confirmed in Node-RED

## Implementation Commands

```bash
# Analyze contacts before sending
python3 /opt/ACTIVE/INFRA/SKILLS/campaign_analytics.py /path/to/contacts.csv

# Check for duplicates
python3 /opt/ACTIVE/INFRA/SKILLS/contact_dedup.py contacts1.csv contacts2.csv

# After campaign - check health
python3 /opt/ACTIVE/INFRA/SKILLS/email_health.py 7
```

---
Plan generated by /opt/ACTIVE/INFRA/SKILLS/brainstorm_campaign.py
"""
    return plan, campaign_name

def calculate_schedule(answers):
    """Calculate send schedule based on answers"""
    schedule = answers.get('schedule', 'Manual trigger')
    volume = answers.get('volume', 'Medium')

    if 'Immediate' in schedule:
        return "Send immediately after approval"
    elif 'tomorrow' in schedule.lower():
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        return f"Start: {tomorrow} 09:00 EET"
    elif '3 days' in schedule:
        return """Spread over 3 days:
- Day 1: 33% of list (morning)
- Day 2: 33% of list (morning)
- Day 3: 34% of list (morning)"""
    elif 'week' in schedule:
        return """Spread over 5 days (Mon-Fri):
- 20% per day
- Send at 09:00-10:00 EET
- Monitor bounce rate daily"""
    else:
        return "Manual trigger via Node-RED or script"

def determine_contacts(answers):
    """Determine contact selection criteria"""
    audience = answers.get('audience', '')
    region = answers.get('region', '')
    email_type = answers.get('email_type', '')

    criteria = []

    if 'Employer' in audience or 'HR' in audience:
        criteria.append("- Corporate emails only (exclude gmail, yahoo, etc.)")
    if 'Job seeker' in audience:
        criteria.append("- Include all email types")

    if 'Nordic' in region:
        criteria.append("- Countries: Finland, Sweden, Norway, Denmark, Iceland")
    elif 'Poland' in region:
        criteria.append("- Country: Poland")
    elif 'Romania' in region:
        criteria.append("- Country: Romania")

    if 'Corporate only' in email_type:
        criteria.append("- Filter: exclude free email providers")
    if 'Verified' in email_type:
        criteria.append("- Filter: only emails with valid MX records")
    if 'New contacts' in email_type:
        criteria.append("- Filter: not in previous campaign lists")

    return '\n'.join(criteria) if criteria else "- All contacts matching region"

def save_plan(plan, campaign_name):
    """Save campaign plan"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    filename = DOCS_DIR / f"{date}-{campaign_name}-plan.md"

    with open(filename, 'w') as f:
        f.write(plan)

    return filename

def non_interactive(name):
    """Generate template plan"""
    return {
        'goal': 'TBD',
        'audience': 'TBD',
        'region': 'TBD',
        'email_type': 'TBD',
        'volume': 'TBD',
        'template': 'Professional/formal',
        'schedule': 'Manual trigger',
        'follow_up': 'Depends on response',
        'campaign_name': name,
        'subject_line': 'TBD',
        'sender_domain': 'interjob.ro'
    }

def main():
    args = sys.argv[1:]

    if '--interactive' in args or not args:
        answers = interactive_session()
        if not answers:
            sys.exit(1)
        plan, name = generate_campaign_plan(answers)
    elif '--name' in args:
        idx = args.index('--name')
        name = args[idx + 1] if idx + 1 < len(args) else 'campaign'
        answers = non_interactive(name)
        plan, name = generate_campaign_plan(answers, name)
    else:
        print("Usage: brainstorm_campaign.py [--interactive] [--name NAME]")
        sys.exit(1)

    filepath = save_plan(plan, name)
    print(f"\n{'='*60}")
    print("CAMPAIGN PLAN GENERATED")
    print(f"{'='*60}")
    print(plan)
    print(f"\nSaved to: {filepath}")

if __name__ == '__main__':
    main()
