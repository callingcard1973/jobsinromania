#!/usr/bin/env python3
"""
Website Generator using LM Studio
Generates simple HTML pages for campaigns and landing pages.

Usage:
    python3 website_generator.py --type landing --sector factory --lang en
    python3 website_generator.py --type jobs --sector horeca --lang ro

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
import argparse
import unicodedata
from typing import Optional
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
from lmstudio_client import LMStudioClient, is_lmstudio_available

PAGE_TYPES = {
    'landing': 'recruitment landing page with call to action',
    'jobs': 'job listings page with positions',
    'about': 'about us company page',
    'contact': 'contact form page'
}

SECTORS = {
    'factory': 'manufacturing and production',
    'horeca': 'hotels, restaurants, tourism',
    'construction': 'building and construction',
    'warehouse': 'logistics and warehousing',
    'healthcare': 'medical and care work'
}


def to_ascii(text: str) -> str:
    """Convert text to ASCII."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFD', str(text))
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn' and ord(c) < 128)


def generate_website(
    page_type: str,
    sector: str,
    lang: str = 'en',
    company: str = 'Interjobs'
) -> Optional[str]:
    """Generate HTML page using LM Studio."""
    if not is_lmstudio_available():
        print("[ERROR] LM Studio not available")
        return None

    type_desc = PAGE_TYPES.get(page_type, page_type)
    sector_desc = SECTORS.get(sector, sector)
    language = "English" if lang == 'en' else "Romanian"

    prompt = f"""Generate a simple HTML {type_desc} for {sector_desc} jobs.
Company: {company}
Language: {language}

Include:
- Clean modern design with inline CSS
- Mobile responsive
- Professional colors (blue/white)
- Clear call to action button
- Contact info placeholder

Output ONLY the HTML code, no explanation:"""

    client = LMStudioClient(timeout=300)
    response = client.query(prompt, temperature=0.5, max_tokens=2000)

    if not response:
        print("[ERROR] No response from LM Studio")
        return None

    # Extract HTML from response
    html = response
    if '```html' in html:
        html = html.split('```html')[1].split('```')[0]
    elif '```' in html:
        html = html.split('```')[1].split('```')[0]

    return to_ascii(html.strip())


def save_html(html: str, output_path: str) -> bool:
    """Save HTML to file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate website pages using LM Studio')
    parser.add_argument('--type', required=True, choices=list(PAGE_TYPES.keys()),
                        help='Page type')
    parser.add_argument('--sector', required=True, choices=list(SECTORS.keys()),
                        help='Industry sector')
    parser.add_argument('--lang', default='en', choices=['en', 'ro'],
                        help='Language')
    parser.add_argument('--company', default='Interjobs',
                        help='Company name')
    parser.add_argument('--output', default=None,
                        help='Output file path')
    parser.add_argument('--test', action='store_true',
                        help='Test mode')

    args = parser.parse_args()

    if args.test:
        print("Testing LM Studio...")
        if is_lmstudio_available():
            print("[OK] LM Studio available")
        else:
            print("[FAIL] LM Studio not available")
        return

    print(f"Generating {args.type} page for {args.sector}...")

    html = generate_website(
        page_type=args.type,
        sector=args.sector,
        lang=args.lang,
        company=args.company
    )

    if not html:
        print("[ERROR] Failed to generate page")
        sys.exit(1)

    if args.output:
        if save_html(html, args.output):
            print(f"[OK] Saved to {args.output}")
    else:
        print(html)


if __name__ == '__main__':
    main()
