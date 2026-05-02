#!/usr/bin/env python3
"""
Template Generator - Generate boilerplate for scrapers, campaigns, and emails
Usage: python3 template_generator.py <type> [options]

Types:
    scraper   - New scraper with CLAUDE.md, config, logging
    campaign  - Campaign plan with segments, templates, schedule
    email     - Email HTML/text templates
    skill     - New skill script skeleton
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict

# ============================================================
# SCRAPER TEMPLATES
# ============================================================

SCRAPER_TEMPLATE = '''#!/usr/bin/env python3
"""
{country} {source_type} Scraper
Scrapes job/contact data from {source_name}

Usage: python3 {filename} [--dry-run] [--max-pages N]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# HTTP client with fallback chain
try:
    import httpx
    HTTP_CLIENT = 'httpx'
except ImportError:
    try:
        import cloudscraper
        HTTP_CLIENT = 'cloudscraper'
    except ImportError:
        import requests
        HTTP_CLIENT = 'requests'

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {{
    'base_url': '{base_url}',
    'output_dir': '/opt/ACTIVE/OPENDATA/DATA/{country}',
    'output_file': '{country_lower}_{source_lower}_{{date}}.csv',
    'max_pages': 100,
    'delay_seconds': 2,
    'timeout': 30,
}}

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/{country}/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# HTTP CLIENT
# ============================================================

def get_client():
    """Get HTTP client with fallback"""
    if HTTP_CLIENT == 'httpx':
        return httpx.Client(timeout=CONFIG['timeout'], follow_redirects=True)
    elif HTTP_CLIENT == 'cloudscraper':
        return cloudscraper.create_scraper()
    else:
        import requests
        return requests.Session()

def fetch_page(url: str, client) -> Optional[str]:
    """Fetch URL with error handling"""
    try:
        headers = {{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}}
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {{url}}: {{e}}")
        return None

# ============================================================
# SCRAPING LOGIC
# ============================================================

def parse_listing_page(html: str) -> List[Dict]:
    """Parse listing page and extract items"""
    items = []
    # TODO: Implement parsing logic
    # Example:
    # from bs4 import BeautifulSoup
    # soup = BeautifulSoup(html, 'html.parser')
    # for item in soup.select('.job-listing'):
    #     items.append({{
    #         'title': item.select_one('.title').text.strip(),
    #         'company': item.select_one('.company').text.strip(),
    #         'url': item.select_one('a')['href'],
    #     }})
    return items

def parse_detail_page(html: str) -> Dict:
    """Parse detail page and extract full data"""
    data = {{}}
    # TODO: Implement detail parsing
    return data

def scrape_all(max_pages: int = None, dry_run: bool = False) -> List[Dict]:
    """Main scraping function"""
    max_pages = max_pages or CONFIG['max_pages']
    results = []

    client = get_client()

    try:
        for page in range(1, max_pages + 1):
            url = f"{{CONFIG['base_url']}}?page={{page}}"
            logger.info(f"Scraping page {{page}}: {{url}}")

            if dry_run:
                logger.info(f"[DRY-RUN] Would fetch: {{url}}")
                continue

            html = fetch_page(url, client)
            if not html:
                break

            items = parse_listing_page(html)
            if not items:
                logger.info(f"No more items on page {{page}}")
                break

            results.extend(items)
            logger.info(f"Found {{len(items)}} items on page {{page}}")

            # Rate limiting
            import time
            time.sleep(CONFIG['delay_seconds'])

    finally:
        if hasattr(client, 'close'):
            client.close()

    return results

# ============================================================
# OUTPUT
# ============================================================

def save_results(results: List[Dict], output_path: str):
    """Save results to CSV"""
    if not results:
        logger.warning("No results to save")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = list(results[0].keys())
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Saved {{len(results)}} results to {{output_path}}")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='{country} {source_type} Scraper')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without fetching')
    parser.add_argument('--max-pages', type=int, default=CONFIG['max_pages'], help='Max pages to scrape')
    parser.add_argument('--output', help='Output file path')
    args = parser.parse_args()

    logger.info(f"Starting {country} {source_type} scraper")
    logger.info(f"Max pages: {{args.max_pages}}, Dry run: {{args.dry_run}}")

    results = scrape_all(max_pages=args.max_pages, dry_run=args.dry_run)

    if results and not args.dry_run:
        date_str = datetime.now().strftime('%Y%m%d')
        output_path = args.output or os.path.join(
            CONFIG['output_dir'],
            CONFIG['output_file'].format(date=date_str)
        )
        save_results(results, output_path)

    logger.info(f"Completed. Total items: {{len(results)}}")

if __name__ == '__main__':
    main()
'''

SCRAPER_CLAUDE_MD = '''# {country} Scraper

## Source
- **URL:** {base_url}
- **Type:** {source_type}
- **Country:** {country}

## Scripts
- `{filename}` - Main scraper

## Schedule
```
# Add to crontab or Node-RED
0 3 * * 0  /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/{country}/{filename}
```

## Output
- Location: `/opt/ACTIVE/OPENDATA/DATA/{country}/`
- Format: CSV with columns: [TODO: list columns]

## Notes
- Rate limit: {delay}s between requests
- Max pages: {max_pages}
'''

# ============================================================
# CAMPAIGN TEMPLATES
# ============================================================

CAMPAIGN_TEMPLATE = '''# Campaign: {name}

## Overview
- **Created:** {date}
- **Type:** {campaign_type}
- **Target:** {target}
- **Goal:** {goal}

## Segments
| Segment | Filter | Count | Priority |
|---------|--------|-------|----------|
| Primary | corporate emails | TBD | High |
| Secondary | personal emails | TBD | Medium |

## Schedule
| Day | Action | Volume |
|-----|--------|--------|
| Day 1 | Initial send | 100 |
| Day 3 | Follow-up 1 | 50 |
| Day 7 | Follow-up 2 | 25 |

## Templates

### Subject Lines (A/B Test)
1. {subject_a}
2. {subject_b}

### Email Body
```
{email_body}
```

## Metrics to Track
- Open rate (target: >20%)
- Click rate (target: >3%)
- Reply rate (target: >1%)
- Bounce rate (target: <5%)

## Data Source
- File: [TODO: specify CSV]
- Columns needed: email, name, company

## Brevo Domain
- Domain: {domain}
- Daily limit: 290

## Notes
{notes}
'''

# ============================================================
# EMAIL TEMPLATES
# ============================================================

EMAIL_TEMPLATES = {
    'cold_outreach': {
        'subject': 'Quick question about {company}',
        'body': '''Hi {name},

I noticed {company} is active in {industry} and wanted to reach out.

{value_proposition}

Would you be open to a quick chat this week?

Best regards,
{sender_name}
{sender_title}
'''
    },
    'follow_up': {
        'subject': 'Following up - {topic}',
        'body': '''Hi {name},

I wanted to follow up on my previous email about {topic}.

{reminder}

Let me know if you have any questions.

Best,
{sender_name}
'''
    },
    'welcome': {
        'subject': 'Welcome to {service}!',
        'body': '''Hi {name},

Welcome to {service}! We're excited to have you on board.

Here's what you can do next:
1. {step_1}
2. {step_2}
3. {step_3}

If you have any questions, just reply to this email.

Best regards,
The {company} Team
'''
    },
    'newsletter': {
        'subject': '{month} Update: {headline}',
        'body': '''Hi {name},

Here's what's new this month:

## {section_1_title}
{section_1_content}

## {section_2_title}
{section_2_content}

---

Best regards,
{sender_name}
'''
    }
}

# ============================================================
# SKILL TEMPLATE
# ============================================================

SKILL_TEMPLATE = '''#!/usr/bin/env python3
"""
{name} - {description}
Usage: python3 {filename} [options]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG = {{
    'output_dir': '/tmp',
}}

# ============================================================
# MAIN LOGIC
# ============================================================

def {main_function}(input_path: str, **kwargs) -> Dict[str, Any]:
    """
    {description}

    Args:
        input_path: Path to input file/directory
        **kwargs: Additional options

    Returns:
        Dict with results
    """
    results = {{
        'input': input_path,
        'timestamp': datetime.now().isoformat(),
    }}

    # TODO: Implement main logic

    return results

# ============================================================
# OUTPUT
# ============================================================

def print_results(results: Dict[str, Any]):
    """Print formatted results"""
    print(f"\\n{{'='*60}}")
    print("{name_upper}")
    print(f"{{'='*60}}\\n")

    for key, value in results.items():
        print(f"{{key}}: {{value}}")

    print(f"\\n{{'='*60}}\\n")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='{description}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  {filename} /path/to/input
  {filename} /path/to/input --output /tmp/output.json
        """
    )

    parser.add_argument('input', nargs='?', help='Input file or directory')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        return

    results = {main_function}(args.input)
    print_results(results)

    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved to: {{args.output}}")

if __name__ == '__main__':
    main()
'''

# ============================================================
# GENERATORS
# ============================================================

def generate_scraper(country: str, source_type: str, source_name: str = None,
                    base_url: str = None, output_dir: str = None) -> Dict[str, str]:
    """Generate scraper files"""
    country = country.upper()
    country_lower = country.lower()
    source_type = source_type.lower().replace(' ', '_')
    source_name = source_name or f"{country} {source_type}"
    base_url = base_url or f"https://example.com/{country_lower}/jobs"

    filename = f"scrape_{source_type}.py"

    output_dir = output_dir or f"/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/{country}"

    # Generate scraper script
    scraper_code = SCRAPER_TEMPLATE.format(
        country=country,
        country_lower=country_lower,
        source_type=source_type,
        source_name=source_name,
        source_lower=source_type.replace('_', ''),
        base_url=base_url,
        filename=filename,
    )

    # Generate CLAUDE.md
    claude_md = SCRAPER_CLAUDE_MD.format(
        country=country,
        source_type=source_type,
        base_url=base_url,
        filename=filename,
        delay=2,
        max_pages=100,
    )

    return {
        'scraper': scraper_code,
        'claude_md': claude_md,
        'filename': filename,
        'output_dir': output_dir,
    }


def generate_campaign(name: str, campaign_type: str = 'cold_email',
                     target: str = None, goal: str = None,
                     domain: str = 'interjob.ro') -> str:
    """Generate campaign plan"""

    subjects = {
        'cold_email': ('Partnership opportunity with {company}', 'Quick question for {name}'),
        'newsletter': ('{month} Jobs Update', 'New opportunities in {industry}'),
        'follow_up': ('Following up on my previous email', 'Did you see my message?'),
    }

    subject_a, subject_b = subjects.get(campaign_type, subjects['cold_email'])

    return CAMPAIGN_TEMPLATE.format(
        name=name,
        date=datetime.now().strftime('%Y-%m-%d'),
        campaign_type=campaign_type,
        target=target or 'HR professionals in Nordic countries',
        goal=goal or 'Generate leads for job placement services',
        subject_a=subject_a,
        subject_b=subject_b,
        email_body='[TODO: Write email body]',
        domain=domain,
        notes='[TODO: Add campaign notes]',
    )


def generate_email(template_type: str, **kwargs) -> Dict[str, str]:
    """Generate email template"""
    if template_type not in EMAIL_TEMPLATES:
        return {'error': f"Unknown template: {template_type}. Available: {list(EMAIL_TEMPLATES.keys())}"}

    template = EMAIL_TEMPLATES[template_type]

    return {
        'subject': template['subject'],
        'body': template['body'],
        'variables': [v.strip('{}') for v in template['body'].split('{') if '}' in v],
    }


def generate_skill(name: str, description: str = None) -> str:
    """Generate skill script skeleton"""
    name_clean = name.lower().replace(' ', '_').replace('-', '_')
    filename = f"{name_clean}.py"

    return SKILL_TEMPLATE.format(
        name=name,
        name_upper=name.upper(),
        description=description or f"{name} skill",
        filename=filename,
        main_function=f"run_{name_clean}",
    )


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Template Generator - Generate boilerplate for scrapers, campaigns, emails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  template_generator.py scraper --country SPAIN --source gov_portal
  template_generator.py scraper --country GREECE --source job_board --url https://example.gr/jobs
  template_generator.py campaign --name "Nordic Q1" --type cold_email
  template_generator.py email --template cold_outreach
  template_generator.py skill --name "data_validator" --desc "Validate CSV data"
        """
    )

    subparsers = parser.add_subparsers(dest='type', help='Template type')

    # Scraper
    scraper_p = subparsers.add_parser('scraper', help='Generate scraper template')
    scraper_p.add_argument('--country', required=True, help='Country name (e.g., SPAIN)')
    scraper_p.add_argument('--source', required=True, help='Source type (e.g., gov_portal, job_board)')
    scraper_p.add_argument('--url', help='Base URL')
    scraper_p.add_argument('--output', help='Output directory')
    scraper_p.add_argument('--write', action='store_true', help='Write files to disk')

    # Campaign
    campaign_p = subparsers.add_parser('campaign', help='Generate campaign plan')
    campaign_p.add_argument('--name', required=True, help='Campaign name')
    campaign_p.add_argument('--type', default='cold_email', help='Campaign type')
    campaign_p.add_argument('--target', help='Target audience')
    campaign_p.add_argument('--goal', help='Campaign goal')
    campaign_p.add_argument('--domain', default='interjob.ro', help='Brevo domain')
    campaign_p.add_argument('--output', help='Output file')

    # Email
    email_p = subparsers.add_parser('email', help='Generate email template')
    email_p.add_argument('--template', required=True,
                        choices=list(EMAIL_TEMPLATES.keys()),
                        help='Template type')

    # Skill
    skill_p = subparsers.add_parser('skill', help='Generate skill script')
    skill_p.add_argument('--name', required=True, help='Skill name')
    skill_p.add_argument('--desc', help='Skill description')
    skill_p.add_argument('--output', help='Output file')
    skill_p.add_argument('--write', action='store_true', help='Write to /opt/ACTIVE/INFRA/SKILLS/')

    args = parser.parse_args()

    if not args.type:
        parser.print_help()
        return

    print(f"\n{'='*60}")
    print("TEMPLATE GENERATOR")
    print(f"{'='*60}\n")

    if args.type == 'scraper':
        result = generate_scraper(
            country=args.country,
            source_type=args.source,
            base_url=args.url,
            output_dir=args.output,
        )

        print(f"Country: {args.country}")
        print(f"Source: {args.source}")
        print(f"Output dir: {result['output_dir']}")
        print(f"Filename: {result['filename']}")

        if args.write:
            os.makedirs(result['output_dir'], exist_ok=True)
            os.makedirs(f"{result['output_dir']}/logs", exist_ok=True)

            scraper_path = f"{result['output_dir']}/{result['filename']}"
            claude_path = f"{result['output_dir']}/CLAUDE.md"

            with open(scraper_path, 'w') as f:
                f.write(result['scraper'])
            os.chmod(scraper_path, 0o755)

            with open(claude_path, 'w') as f:
                f.write(result['claude_md'])

            print(f"\nWritten:")
            print(f"  {scraper_path}")
            print(f"  {claude_path}")
        else:
            print(f"\n--- {result['filename']} ---")
            print(result['scraper'][:2000])
            print("...\n")
            print("Use --write to create files")

    elif args.type == 'campaign':
        result = generate_campaign(
            name=args.name,
            campaign_type=args.type,
            target=args.target,
            goal=args.goal,
            domain=args.domain,
        )

        if args.output:
            with open(args.output, 'w') as f:
                f.write(result)
            print(f"Saved to: {args.output}")
        else:
            print(result)

    elif args.type == 'email':
        result = generate_email(args.template)

        if 'error' in result:
            print(result['error'])
        else:
            print(f"Template: {args.template}")
            print(f"\nSubject: {result['subject']}")
            print(f"\nBody:\n{result['body']}")
            print(f"\nVariables: {', '.join(result['variables'])}")

    elif args.type == 'skill':
        result = generate_skill(args.name, args.desc)

        if args.write:
            filename = f"{args.name.lower().replace(' ', '_')}.py"
            path = f"/opt/ACTIVE/INFRA/SKILLS/{filename}"
            with open(path, 'w') as f:
                f.write(result)
            os.chmod(path, 0o755)
            print(f"Written: {path}")
        elif args.output:
            with open(args.output, 'w') as f:
                f.write(result)
            print(f"Saved to: {args.output}")
        else:
            print(result[:2000])
            print("...\n")
            print("Use --write to create in /opt/ACTIVE/INFRA/SKILLS/")

    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
