#!/usr/bin/env python3
"""
PLAN27 Country File Consolidator

Manages country CLAUDE.md files from a single YAML source and template.

Usage:
    python3 plan27_consolidator.py --generate-all     # Regenerate all country files
    python3 plan27_consolidator.py --generate NO      # Regenerate single country
    python3 plan27_consolidator.py --extract          # Extract data from existing files
    python3 plan27_consolidator.py --validate         # Validate yaml data
    python3 plan27_consolidator.py --diff NO          # Show diff for country
    python3 plan27_consolidator.py --status           # Show summary
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Paths
BASE_DIR = Path("/opt/ACTIVE/PROJECTS/PLAN27/COUNTRIES")
TEMPLATE_PATH = BASE_DIR / "TEMPLATE.md"
YAML_PATH = BASE_DIR / "countries.yaml"


def load_yaml() -> dict:
    """Load countries configuration from YAML."""
    if not YAML_PATH.exists():
        print(f"ERROR: {YAML_PATH} not found")
        sys.exit(1)

    with open(YAML_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_template() -> str:
    """Load the Jinja2-style template."""
    if not TEMPLATE_PATH.exists():
        print(f"ERROR: {TEMPLATE_PATH} not found")
        sys.exit(1)

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def render_template(template: str, data: dict) -> str:
    """
    Simple Jinja2-style template rendering without the Jinja2 dependency.
    Supports: {{ var }}, {% for %}, {% if %}, {% endif %}, {% endfor %}
    """
    result = template
    updated = datetime.now().strftime("%Y-%m-%d")

    # Add computed fields
    data['updated'] = updated

    # Handle simple variable substitution first
    for key, value in data.items():
        if isinstance(value, str):
            result = result.replace('{{ ' + key + ' }}', value)

    # Handle list iterations with for loops
    # Pattern: {% for item in items %} ... {{ item }} ... {% endfor %}
    for_pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'

    def replace_for(match):
        item_var = match.group(1)
        list_var = match.group(2)
        body = match.group(3)

        items = data.get(list_var, [])
        if not items:
            return ""

        rendered_items = []
        for item in items:
            item_body = body.replace('{{ ' + item_var + ' }}', str(item))
            # Strip leading/trailing whitespace but preserve the line content
            item_body = item_body.strip()
            rendered_items.append(item_body)

        return '\n'.join(rendered_items)

    result = re.sub(for_pattern, replace_for, result, flags=re.DOTALL)

    # Handle if conditions
    # Pattern: {% if var %} ... {% endif %}
    if_pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'

    def replace_if(match):
        var_name = match.group(1)
        body = match.group(2)

        value = data.get(var_name)
        if value:
            return body.strip()
        return ""

    result = re.sub(if_pattern, replace_if, result, flags=re.DOTALL)

    # Handle if not conditions
    # Pattern: {% if not var %} ... {% endif %}
    if_not_pattern = r'\{%\s*if\s+not\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'

    def replace_if_not(match):
        var_name = match.group(1)
        body = match.group(2)

        value = data.get(var_name)
        if not value:
            return body.strip()
        return ""

    result = re.sub(if_not_pattern, replace_if_not, result, flags=re.DOTALL)

    # Handle elif conditions (tier_type comparisons)
    elif_pattern = r'\{%\s*elif\s+(\w+)\s*==\s*"(\w+)"\s*%\}(.*?)(?=\{%\s*(?:elif|else|endif))'

    # Simplified: handle the tier_type conditionals as a whole block
    tier_block_pattern = (
        r'\{%\s*if\s+tier_type\s*==\s*"TARGET"\s*%\}(.*?)'
        r'\{%\s*elif\s+tier_type\s*==\s*"SOURCE"\s*%\}(.*?)'
        r'\{%\s*else\s*%\}(.*?)'
        r'\{%\s*endif\s*%\}'
    )

    def replace_tier_block(match):
        target_body = match.group(1).strip()
        source_body = match.group(2).strip()
        other_body = match.group(3).strip()

        tier_type = data.get('tier_type', '')
        if tier_type == 'TARGET':
            return target_body
        elif tier_type == 'SOURCE':
            return source_body
        else:
            return other_body

    result = re.sub(tier_block_pattern, replace_tier_block, result, flags=re.DOTALL)

    # Handle filter: {{ code | upper }}
    filter_pattern = r'\{\{\s*(\w+)\s*\|\s*upper\s*\}\}'

    def replace_filter(match):
        var_name = match.group(1)
        value = data.get(var_name, '')
        return str(value).upper()

    result = re.sub(filter_pattern, replace_filter, result)

    # Clean up multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result


def generate_country_file(code: str, data: dict, template: str, dry_run: bool = False) -> str:
    """Generate CLAUDE.md for a single country."""
    country_dir = BASE_DIR / code
    output_path = country_dir / "CLAUDE.md"

    rendered = render_template(template, data)

    if dry_run:
        return rendered

    # Ensure directory exists
    country_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered)

    return rendered


def generate_all(dry_run: bool = False) -> None:
    """Generate all country files."""
    config = load_yaml()
    template = load_template()

    countries = config.get('countries', {})

    print(f"Generating {len(countries)} country files...")

    for code, data in countries.items():
        generate_country_file(code, data, template, dry_run)
        print(f"  Generated: {code}/CLAUDE.md")

    print(f"\nDone. {len(countries)} files generated.")


def extract_from_existing() -> dict:
    """Extract data from existing CLAUDE.md files to YAML format."""
    countries = {}

    for country_dir in sorted(BASE_DIR.iterdir()):
        if not country_dir.is_dir():
            continue

        claude_path = country_dir / "CLAUDE.md"
        if not claude_path.exists():
            continue

        code = country_dir.name
        if code == "CLAUDE":  # Skip CLAUDE directory
            continue

        with open(claude_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract fields using regex
        data = {'code': code}

        # Country name from title
        title_match = re.search(r'^#\s+(\w+(?:\s+\w+)?)\s+\((\w+)\)', content, re.MULTILINE)
        if title_match:
            data['country'] = title_match.group(1)

        # Table fields
        tier_match = re.search(r'\|\s*Tier\s*\|\s*(.+?)\s*\|', content)
        if tier_match:
            data['tier'] = tier_match.group(1).strip()

        priority_match = re.search(r'\|\s*Priority\s*\|\s*(.+?)\s*\|', content)
        if priority_match:
            data['priority'] = priority_match.group(1).strip()

        sectors_match = re.search(r'\|\s*Sectors\s*\|\s*(.+?)\s*\|', content)
        if sectors_match:
            data['sectors'] = sectors_match.group(1).strip()

        # Data paths
        data_paths = re.findall(r'^-\s*`([^`]+)`\s*$', content, re.MULTILINE)
        if data_paths:
            data['data_paths'] = data_paths

        # Scrapers
        scraper_section = re.search(r'## Scrapers\n\n(.*?)(?=\n---|\n##)', content, re.DOTALL)
        if scraper_section:
            scrapers = re.findall(r'^-\s+(.+)$', scraper_section.group(1), re.MULTILINE)
            if scrapers and scrapers[0] != 'No scrapers implemented yet':
                data['scrapers'] = scrapers

        # TODOs
        todos = re.findall(r'^-\s*\[\s*\]\s+(.+)$', content, re.MULTILINE)
        if todos:
            data['todos'] = todos

        countries[code] = data

    return {'countries': countries}


def validate_yaml() -> bool:
    """Validate YAML data completeness."""
    config = load_yaml()
    countries = config.get('countries', {})

    required_fields = ['country', 'code', 'tier', 'priority', 'sectors']
    errors = []
    warnings = []

    for code, data in countries.items():
        # Check required fields
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"{code}: Missing required field '{field}'")

        # Check optional fields
        if not data.get('data_paths'):
            warnings.append(f"{code}: No data_paths defined")

        if not data.get('scrapers'):
            warnings.append(f"{code}: No scrapers defined")

    print(f"Validated {len(countries)} countries\n")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - {w}")

    if not errors and not warnings:
        print("All countries valid!")

    return len(errors) == 0


def show_diff(code: str) -> None:
    """Show diff between current and generated file."""
    config = load_yaml()
    template = load_template()

    countries = config.get('countries', {})
    if code not in countries:
        print(f"ERROR: Country '{code}' not found in YAML")
        return

    data = countries[code]
    new_content = generate_country_file(code, data, template, dry_run=True)

    current_path = BASE_DIR / code / "CLAUDE.md"
    if current_path.exists():
        with open(current_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        current_content = ""

    if current_content == new_content:
        print(f"{code}: No changes")
    else:
        print(f"{code}: Changes detected")
        print("\n--- Current ---")
        print(current_content[:500] + "..." if len(current_content) > 500 else current_content)
        print("\n--- Generated ---")
        print(new_content[:500] + "..." if len(new_content) > 500 else new_content)


def show_status() -> None:
    """Show summary of all countries."""
    config = load_yaml()
    countries = config.get('countries', {})

    # Group by tier
    tiers = {}
    for code, data in countries.items():
        tier = data.get('tier', 'Unknown')
        if tier not in tiers:
            tiers[tier] = []
        priority = data.get('priority', 'UNKNOWN')
        if isinstance(priority, bool):
            priority = 'HIGH' if priority else 'LOW'
        tiers[tier].append((code, str(priority)))

    print(f"PLAN27 Countries Summary: {len(countries)} total\n")

    for tier in sorted(tiers.keys()):
        print(f"{tier}:")
        for code, priority in sorted(tiers[tier], key=lambda x: str(x[0])):
            print(f"  {code}: {priority}")
        print()

    # Files status
    print("File Status:")
    existing = 0
    missing = 0
    for code in countries:
        path = BASE_DIR / code / "CLAUDE.md"
        if path.exists():
            existing += 1
        else:
            missing += 1
            print(f"  MISSING: {code}/CLAUDE.md")

    print(f"\n  Existing: {existing}")
    print(f"  Missing: {missing}")


def main():
    parser = argparse.ArgumentParser(description='PLAN27 Country File Consolidator')
    parser.add_argument('--generate-all', action='store_true', help='Regenerate all country files')
    parser.add_argument('--generate', metavar='CODE', help='Regenerate single country file')
    parser.add_argument('--extract', action='store_true', help='Extract data from existing files to stdout')
    parser.add_argument('--validate', action='store_true', help='Validate YAML data')
    parser.add_argument('--diff', metavar='CODE', help='Show diff for country')
    parser.add_argument('--status', action='store_true', help='Show summary')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')

    args = parser.parse_args()

    if args.generate_all:
        generate_all(args.dry_run)
    elif args.generate:
        config = load_yaml()
        template = load_template()
        countries = config.get('countries', {})

        code = args.generate.upper()
        if code not in countries:
            print(f"ERROR: Country '{code}' not found in YAML")
            sys.exit(1)

        data = countries[code]
        result = generate_country_file(code, data, template, args.dry_run)

        if args.dry_run:
            print(result)
        else:
            print(f"Generated: {code}/CLAUDE.md")
    elif args.extract:
        extracted = extract_from_existing()
        print(yaml.dump(extracted, default_flow_style=False, allow_unicode=True, sort_keys=False))
    elif args.validate:
        success = validate_yaml()
        sys.exit(0 if success else 1)
    elif args.diff:
        show_diff(args.diff.upper())
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
