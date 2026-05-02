#!/usr/bin/env python3
"""
Scraper Design Brainstorming - Structured design for new scrapers
Usage: python3 brainstorm_scraper.py [--interactive] [--country NAME]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import json
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path('/opt/ACTIVE/SCRAPERS/EUROPE/docs/plans')
TEMPLATE_DIR = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE')

QUESTIONS = {
    'country': {
        'q': 'What country/region is this scraper for?',
        'opts': ['Nordic (FI/SE/NO/DK/IS)', 'Eastern Europe', 'Western Europe', 'UK/Ireland', 'Other']
    },
    'source_type': {
        'q': 'What type of job source?',
        'opts': ['Government job portal', 'Private job board', 'Company career pages', 'Recruitment agencies', 'Multiple sources']
    },
    'auth_required': {
        'q': 'Does the site require authentication?',
        'opts': ['No - public access', 'Yes - free registration', 'Yes - paid subscription', 'API key required']
    },
    'anti_bot': {
        'q': 'What anti-bot protection exists?',
        'opts': ['None detected', 'Cloudflare', 'reCAPTCHA', 'Rate limiting only', 'Unknown - needs testing']
    },
    'data_format': {
        'q': 'How is job data structured?',
        'opts': ['Clean HTML/JSON API', 'JavaScript rendered', 'PDF documents', 'Mixed formats', 'Unknown']
    },
    'volume': {
        'q': 'Expected job volume?',
        'opts': ['Small (<1000 jobs)', 'Medium (1000-10000)', 'Large (10000-50000)', 'Very large (50000+)']
    },
    'update_freq': {
        'q': 'How often should it run?',
        'opts': ['Daily', 'Weekly', 'Bi-weekly', 'Monthly', 'On-demand only']
    },
    'contact_fields': {
        'q': 'What contact info is available?',
        'opts': ['Email + phone + company', 'Email only', 'Company website only', 'Apply via portal', 'Varies by listing']
    }
}

def get_existing_scrapers():
    """List existing scraper countries"""
    if TEMPLATE_DIR.exists():
        return [d.name for d in TEMPLATE_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
    return []

def interactive_session():
    """Run interactive Q&A session"""
    print(f"\n{'='*60}")
    print("SCRAPER DESIGN BRAINSTORMING")
    print(f"{'='*60}\n")

    answers = {}
    existing = get_existing_scrapers()
    print(f"Existing scrapers: {', '.join(existing[:10])}{'...' if len(existing)>10 else ''}\n")

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
                elif choice:  # Custom answer
                    answers[key] = choice
                    break
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return None

    # Additional details
    print("\nAdditional details (press Enter to skip):")
    answers['url'] = input("Target URL: ").strip() or "TBD"
    answers['notes'] = input("Special notes: ").strip() or "None"

    return answers

def generate_design(answers, country_name=None):
    """Generate design document from answers"""
    date = datetime.now().strftime('%Y-%m-%d')
    country = country_name or answers.get('country', 'unknown').split()[0].lower()

    # Determine recommended approach
    approach = determine_approach(answers)

    design = f"""# Scraper Design: {country.upper()}
Generated: {date}

## Overview
- **Country/Region**: {answers.get('country', 'Unknown')}
- **Source Type**: {answers.get('source_type', 'Unknown')}
- **Target URL**: {answers.get('url', 'TBD')}

## Technical Assessment

### Authentication
{answers.get('auth_required', 'Unknown')}

### Anti-Bot Protection
{answers.get('anti_bot', 'Unknown')}
{get_anti_bot_recommendation(answers.get('anti_bot', ''))}

### Data Format
{answers.get('data_format', 'Unknown')}

## Data Specification

### Volume
- Expected: {answers.get('volume', 'Unknown')}
- Update frequency: {answers.get('update_freq', 'Unknown')}

### Contact Fields
{answers.get('contact_fields', 'Unknown')}

## Recommended Approach

{approach}

## Implementation Checklist

- [ ] Test URL accessibility from raspibig
- [ ] Identify pagination pattern
- [ ] Map contact field selectors
- [ ] Create scraper script in /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/{country.upper()}/
- [ ] Add to Node-RED schedule
- [ ] Test with small batch (10 jobs)
- [ ] Full run and verify output
- [ ] Add CLAUDE.md documentation

## Fallback Chain
1. httpx (fastest)
2. cloudscraper (if Cloudflare)
3. requests (basic)
4. Playwright Firefox (JS rendering)

## Notes
{answers.get('notes', 'None')}

---
Design generated by /opt/ACTIVE/INFRA/SKILLS/brainstorm_scraper.py
"""
    return design, country

def determine_approach(answers):
    """Determine best scraping approach based on answers"""
    anti_bot = answers.get('anti_bot', '')
    data_format = answers.get('data_format', '')

    if 'Cloudflare' in anti_bot:
        return """**Use cloudscraper + rotating delays**
- Start with cloudscraper library
- Add 2-5 second random delays
- Rotate User-Agent strings
- Consider proxy if blocked"""

    if 'JavaScript' in data_format:
        return """**Use Playwright Firefox**
- JavaScript rendering required
- Use headless Firefox (Chromium broken on Pi)
- Wait for dynamic content load
- Extract from rendered DOM"""

    if 'API' in data_format or 'JSON' in data_format:
        return """**Use httpx with JSON parsing**
- Direct API calls preferred
- Fastest and most reliable
- Parse JSON response directly
- Check for pagination in API"""

    if 'reCAPTCHA' in anti_bot:
        return """**Manual or API-based approach**
- reCAPTCHA blocking automation
- Consider: official API, RSS feed, or manual data entry
- Check for mobile site (often less protection)"""

    return """**Standard httpx approach**
- Start with httpx + BeautifulSoup
- Add delays if rate limited
- Fall back to cloudscraper if needed"""

def get_anti_bot_recommendation(anti_bot):
    """Get specific anti-bot recommendations"""
    if 'Cloudflare' in anti_bot:
        return "**Recommendation**: Use cloudscraper library, not raw requests"
    if 'reCAPTCHA' in anti_bot:
        return "**Warning**: May need alternative approach (API, RSS, etc.)"
    if 'Rate limiting' in anti_bot:
        return "**Recommendation**: Add 3-5 second delays between requests"
    return ""

def save_design(design, country):
    """Save design document"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    filename = DOCS_DIR / f"{date}-{country}-scraper-design.md"

    with open(filename, 'w') as f:
        f.write(design)

    return filename

def non_interactive(country):
    """Generate template design for a country"""
    answers = {
        'country': country,
        'source_type': 'TBD - needs research',
        'auth_required': 'TBD',
        'anti_bot': 'Unknown - needs testing',
        'data_format': 'Unknown',
        'volume': 'TBD',
        'update_freq': 'Weekly',
        'contact_fields': 'TBD',
        'url': 'TBD',
        'notes': f'Auto-generated template for {country}'
    }
    return answers

def main():
    args = sys.argv[1:]

    if '--interactive' in args or not args:
        answers = interactive_session()
        if not answers:
            sys.exit(1)
        design, country = generate_design(answers)
    elif '--country' in args:
        idx = args.index('--country')
        country = args[idx + 1] if idx + 1 < len(args) else 'unknown'
        answers = non_interactive(country)
        design, country = generate_design(answers, country)
    else:
        print("Usage: brainstorm_scraper.py [--interactive] [--country NAME]")
        sys.exit(1)

    # Save and display
    filepath = save_design(design, country)
    print(f"\n{'='*60}")
    print("DESIGN DOCUMENT GENERATED")
    print(f"{'='*60}")
    print(design)
    print(f"\nSaved to: {filepath}")

if __name__ == '__main__':
    main()
