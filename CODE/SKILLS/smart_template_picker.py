#!/usr/bin/env python3
"""
Smart Template Picker - LLM picks best template per contact

Uses local LLM to select most appropriate template based on:
- Company type/sector
- Country/language
- Previous interactions
- Lead score

Usage:
    python3 smart_template_picker.py --contact user@company.com
    python3 smart_template_picker.py --campaign HORECA2026 --limit 10
    python3 smart_template_picker.py --test               # Test with sample
    python3 smart_template_picker.py --status             # Show picker stats

No external tokens - uses localhost:1234 LLM.
"""

import os
import sys
import csv
import json
import re
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

# Paths
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.template_picker_state.json")
LLM_URL = "http://localhost:1234/v1/chat/completions"

# Country to language mapping
COUNTRY_LANG = {
    "RO": "romanian",
    "PL": "polish",
    "CZ": "czech",
    "DE": "german",
    "HU": "hungarian",
    "BG": "bulgarian",
    "SK": "slovak",
    "HR": "croatian",
    "SI": "slovenian",
    "AT": "german",
    "CH": "german",
    "NL": "dutch",
    "BE": "dutch",
    "FR": "french",
    "ES": "spanish",
    "IT": "italian",
    "PT": "portuguese",
    "UK": "english",
    "IE": "english",
    "SE": "english",
    "NO": "english",
    "DK": "english",
    "FI": "english",
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"picks": {}, "stats": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_available_templates(campaign_name):
    """Get available templates for campaign."""
    templates = {}
    template_dir = CAMPAIGNS_DIR / campaign_name / "templates"

    if not template_dir.exists():
        return templates

    for template_file in template_dir.glob("*.txt"):
        try:
            with open(template_file, 'r') as f:
                content = f.read()

            # Extract subject
            subject = ""
            for line in content.split('\n'):
                if line.startswith('Subject:'):
                    subject = line[8:].strip()
                    break

            templates[template_file.stem] = {
                'path': str(template_file),
                'subject': subject,
                'preview': content[:200],
                'language': detect_template_language(template_file.stem, content)
            }
        except:
            pass

    return templates


def detect_template_language(filename, content):
    """Detect template language from filename or content."""
    filename_lower = filename.lower()

    # Check filename
    for lang in ['polish', 'german', 'czech', 'romanian', 'hungarian', 'english', 'french', 'spanish']:
        if lang in filename_lower or lang[:2] in filename_lower:
            return lang

    # Check for language indicators in content
    content_lower = content.lower()
    if any(w in content_lower for w in ['dzien dobry', 'pozdrawiam', 'z powazaniem']):
        return 'polish'
    if any(w in content_lower for w in ['sehr geehrte', 'mit freundlichen', 'gruessen']):
        return 'german'
    if any(w in content_lower for w in ['dobry den', 'dekujeme', 's pozdravem']):
        return 'czech'
    if any(w in content_lower for w in ['buna ziua', 'multumim', 'cu stima']):
        return 'romanian'

    return 'english'


def detect_contact_language(contact):
    """Detect preferred language for contact."""
    country = contact.get('country', '').upper()
    if country in COUNTRY_LANG:
        return COUNTRY_LANG[country]

    # Check email domain
    email = contact.get('email', '').lower()
    if '.pl' in email:
        return 'polish'
    if '.de' in email or '.at' in email:
        return 'german'
    if '.cz' in email:
        return 'czech'
    if '.ro' in email:
        return 'romanian'

    return 'english'


def pick_template_rules(contact, templates):
    """Rule-based template selection (fast, no LLM)."""
    contact_lang = detect_contact_language(contact)

    # Find templates matching language
    matching = []
    for name, info in templates.items():
        if info['language'] == contact_lang:
            matching.append((name, info, 100))
        elif info['language'] == 'english':
            matching.append((name, info, 50))

    if not matching:
        # Return first template as fallback
        first = list(templates.items())[0]
        return first[0], first[1], "fallback"

    # Sort by score
    matching.sort(key=lambda x: -x[2])

    return matching[0][0], matching[0][1], f"rule:{contact_lang}"


def pick_template_llm(contact, templates):
    """LLM-based template selection (smarter, slower)."""
    contact_lang = detect_contact_language(contact)

    # Prepare template summaries
    template_list = []
    for name, info in templates.items():
        template_list.append(f"- {name}: {info['language']}, subject: {info['subject'][:50]}")

    prompt = f"""Select the best email template for this contact:

Contact:
- Company: {contact.get('company', 'Unknown')}
- Country: {contact.get('country', 'Unknown')}
- Sector: {contact.get('sector', 'Unknown')}
- Preferred language: {contact_lang}

Available templates:
{chr(10).join(template_list)}

Reply with ONLY the template name (e.g., "01_intro" or "polish_horeca"):"""

    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "llama-3.2-3b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 30,
                "temperature": 0.1
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            selected = result['choices'][0]['message']['content'].strip()
            # Clean up
            selected = re.sub(r'[^\w_-]', '', selected)

            if selected in templates:
                return selected, templates[selected], "llm"
    except Exception as e:
        log(f"LLM error: {e}")

    # Fallback to rules
    return pick_template_rules(contact, templates)


def pick_template(contact, campaign_name, use_llm=True):
    """Pick best template for contact."""
    templates = get_available_templates(campaign_name)

    if not templates:
        return None, None, "no_templates"

    if len(templates) == 1:
        name, info = list(templates.items())[0]
        return name, info, "only_one"

    if use_llm:
        return pick_template_llm(contact, templates)
    else:
        return pick_template_rules(contact, templates)


def process_campaign_contacts(campaign_name, limit=10, use_llm=True):
    """Pick templates for campaign contacts."""
    contacts_file = CAMPAIGNS_DIR / campaign_name / "contacts" / "contacts.csv"

    if not contacts_file.exists():
        log(f"No contacts for {campaign_name}")
        return []

    results = []

    with open(contacts_file, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break

            template_name, template_info, method = pick_template(row, campaign_name, use_llm)

            results.append({
                'email': row.get('email', ''),
                'company': row.get('company', ''),
                'template': template_name,
                'language': template_info.get('language', '') if template_info else '',
                'method': method
            })

    return results


def show_status():
    """Show picker status."""
    state = load_state()

    print("\n=== Smart Template Picker Status ===\n")

    stats = state.get('stats', {})
    print(f"Total picks: {sum(stats.values())}")

    if stats:
        print("\nBy method:")
        for method, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {method}: {count}")

    print("\nAvailable campaigns:")
    for campaign_dir in CAMPAIGNS_DIR.iterdir():
        if campaign_dir.is_dir():
            templates = get_available_templates(campaign_dir.name)
            if templates:
                print(f"  {campaign_dir.name}: {len(templates)} templates")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Smart Template Picker")
    parser.add_argument("--contact", help="Pick template for email")
    parser.add_argument("--campaign", help="Campaign name")
    parser.add_argument("--limit", type=int, default=10, help="Limit contacts")
    parser.add_argument("--no-llm", action="store_true", help="Use rules only")
    parser.add_argument("--test", action="store_true", help="Test with sample")
    parser.add_argument("--status", action="store_true", help="Show status")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.test:
        test_contact = {
            'email': 'test@company.pl',
            'company': 'Test Hotel Sp. z o.o.',
            'country': 'PL',
            'sector': 'horeca'
        }
        print("Testing with sample contact:")
        print(json.dumps(test_contact, indent=2))

        for campaign in ['LUCIAN_HORECA_2026', 'HORECA2026']:
            templates = get_available_templates(campaign)
            if templates:
                name, info, method = pick_template(test_contact, campaign, use_llm=not args.no_llm)
                print(f"\n{campaign}: {name} ({method})")
                break
        return

    if args.campaign:
        results = process_campaign_contacts(args.campaign, args.limit, use_llm=not args.no_llm)
        print(f"\n=== {args.campaign} Template Picks ===\n")
        for r in results:
            print(f"{r['email']}: {r['template']} ({r['language']}) [{r['method']}]")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
