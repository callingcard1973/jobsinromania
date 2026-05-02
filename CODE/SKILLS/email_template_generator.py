#!/usr/bin/env python3
"""
Email Template Generator using LM Studio
Generates ASCII-only email templates for campaigns.

Usage:
    python3 email_template_generator.py --sector factory --audience workers --goal recruitment --lang en
    python3 email_template_generator.py --sector horeca --audience employers --goal partnership --lang ro

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
import argparse
import unicodedata
from typing import Optional, List, Dict

sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
from lmstudio_client import LMStudioClient, is_lmstudio_available

# Sector descriptions for context
SECTORS = {
    'factory': 'manufacturing, production, assembly line, industrial',
    'horeca': 'hotels, restaurants, catering, hospitality, tourism',
    'construction': 'building, civil engineering, infrastructure',
    'warehouse': 'logistics, storage, distribution, fulfillment',
    'agriculture': 'farming, seasonal work, harvest, food production',
    'healthcare': 'nursing, elderly care, medical assistance',
    'transport': 'driving, delivery, trucking, logistics',
    'cleaning': 'housekeeping, janitorial, sanitation',
    'meat': 'meat processing, slaughterhouse, food processing',
    'electric': 'electrical work, wiring, installation',
    'mechanic': 'automotive repair, machinery, maintenance'
}

AUDIENCES = {
    'workers': 'job seekers looking for employment opportunities',
    'employers': 'companies and businesses looking to hire workers',
    'agencies': 'recruitment agencies and staffing companies'
}

GOALS = {
    'recruitment': 'recruiting workers for job positions',
    'partnership': 'establishing business partnerships',
    'information': 'sharing information about services',
    'followup': 'following up on previous communication'
}


def to_ascii(text: str) -> str:
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFD', str(text))
    ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn' and ord(c) < 128)
    # Replace common special chars
    ascii_text = ascii_text.replace('"', '"').replace('"', '"')
    ascii_text = ascii_text.replace(''', "'").replace(''', "'")
    ascii_text = ascii_text.replace('–', '-').replace('—', '-')
    ascii_text = ascii_text.replace('•', '-').replace('…', '...')
    return ascii_text


def generate_template(
    sector: str,
    audience: str,
    goal: str,
    lang: str = 'en',
    company_context: str = None,
    num_variations: int = 3
) -> Optional[List[Dict[str, str]]]:
    """
    Generate email templates using LM Studio.

    Args:
        sector: Industry sector (factory, horeca, etc.)
        audience: Target audience (workers, employers, agencies)
        goal: Campaign goal (recruitment, partnership, etc.)
        lang: Language (en, ro)
        company_context: Additional context about the company
        num_variations: Number of template variations to generate

    Returns:
        List of dicts with 'subject' and 'body' keys
    """
    if not is_lmstudio_available():
        print("[ERROR] LM Studio not available")
        return None

    sector_desc = SECTORS.get(sector, sector)
    audience_desc = AUDIENCES.get(audience, audience)
    goal_desc = GOALS.get(goal, goal)

    language = "English" if lang == 'en' else "Romanian"
    context = company_context or "Interjobs - European recruitment agency"

    system_prompt = "You write short professional emails. ASCII only. Use {company} {name} placeholders."

    prompt = f"""Write {num_variations} short {language} email(s) for {sector} {goal} to {audience}.

Format each as:
SUBJECT: [max 50 chars]
BODY:
[max 100 words]

Start now:"""

    client = LMStudioClient(timeout=300)
    response = client.query(prompt, system_prompt=system_prompt, temperature=0.7, max_tokens=1000)

    if not response:
        print("[ERROR] No response from LM Studio")
        return None

    # Parse response into variations
    templates = []
    current_subject = None
    current_body = []
    in_body = False

    for line in response.split('\n'):
        line = line.strip()

        if line.startswith('SUBJECT:'):
            # Save previous template if exists
            if current_subject and current_body:
                body_text = '\n'.join(current_body).strip()
                templates.append({
                    'subject': to_ascii(current_subject),
                    'body': to_ascii(body_text)
                })
                current_body = []

            current_subject = line.replace('SUBJECT:', '').strip()
            in_body = False

        elif line.startswith('BODY:'):
            in_body = True

        elif line.startswith('VARIATION') and ':' in line:
            # New variation marker - save previous if exists
            if current_subject and current_body:
                body_text = '\n'.join(current_body).strip()
                templates.append({
                    'subject': to_ascii(current_subject),
                    'body': to_ascii(body_text)
                })
                current_subject = None
                current_body = []
                in_body = False

        elif in_body:
            current_body.append(line)

    # Don't forget the last template
    if current_subject and current_body:
        body_text = '\n'.join(current_body).strip()
        templates.append({
            'subject': to_ascii(current_subject),
            'body': to_ascii(body_text)
        })

    return templates[:num_variations] if templates else None


def save_template(template: Dict[str, str], output_path: str) -> bool:
    """Save a template to file in campaign format."""
    try:
        content = f"Subject: {template['subject']}\n\n{template['body']}"
        with open(output_path, 'w', encoding='ascii', errors='replace') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save template: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate email templates using LM Studio')
    parser.add_argument('--sector', required=True, choices=list(SECTORS.keys()),
                        help='Industry sector')
    parser.add_argument('--audience', required=True, choices=list(AUDIENCES.keys()),
                        help='Target audience')
    parser.add_argument('--goal', required=True, choices=list(GOALS.keys()),
                        help='Campaign goal')
    parser.add_argument('--lang', default='en', choices=['en', 'ro'],
                        help='Language (default: en)')
    parser.add_argument('--context', default=None,
                        help='Additional company context')
    parser.add_argument('--variations', type=int, default=3,
                        help='Number of variations (default: 3)')
    parser.add_argument('--output', default=None,
                        help='Output directory for templates')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - show connection status only')

    args = parser.parse_args()

    if args.test:
        print("Testing LM Studio connection...")
        if is_lmstudio_available():
            print("[OK] LM Studio is available")
            client = LMStudioClient()
            print(f"Models: {client.get_available_models()}")
        else:
            print("[FAIL] LM Studio not available")
        return

    print(f"Generating {args.variations} templates...")
    print(f"  Sector: {args.sector}")
    print(f"  Audience: {args.audience}")
    print(f"  Goal: {args.goal}")
    print(f"  Language: {args.lang}")
    print()

    templates = generate_template(
        sector=args.sector,
        audience=args.audience,
        goal=args.goal,
        lang=args.lang,
        company_context=args.context,
        num_variations=args.variations
    )

    if not templates:
        print("[ERROR] Failed to generate templates")
        sys.exit(1)

    for i, template in enumerate(templates, 1):
        print(f"=== VARIATION {i} ===")
        print(f"Subject: {template['subject']}")
        print()
        print(template['body'])
        print()

        if args.output:
            import os
            os.makedirs(args.output, exist_ok=True)
            output_path = os.path.join(args.output, f"template_{i:02d}.txt")
            if save_template(template, output_path):
                print(f"  Saved to: {output_path}")
            print()

    print(f"[OK] Generated {len(templates)} templates")


if __name__ == '__main__':
    main()
