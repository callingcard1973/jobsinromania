#!/usr/bin/env python3
"""
Scraper CLAUDE.md Consolidator

Manages scraper CLAUDE.md files from a single YAML source and template.

Usage:
    python3 scraper_consolidator.py --status              # Show summary of all scrapers
    python3 scraper_consolidator.py --generate NORWAY     # Regenerate single scraper file
    python3 scraper_consolidator.py --generate-all        # Regenerate all scraper files
    python3 scraper_consolidator.py --extract             # Extract data from existing files
    python3 scraper_consolidator.py --validate            # Validate yaml data
    python3 scraper_consolidator.py --diff NORWAY         # Show diff for scraper
    python3 scraper_consolidator.py --list                # List all scrapers
    python3 scraper_consolidator.py --list --type country # List scrapers by type
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


# Paths
BASE_DIR = Path("/opt/ACTIVE/SCRAPERS")
TEMPLATE_PATH = BASE_DIR / "TEMPLATE.md"
YAML_PATH = BASE_DIR / "scrapers.yaml"


def load_yaml() -> dict:
    """Load scrapers configuration from YAML."""
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


def get_defaults(config: dict) -> dict:
    """Get default values from config."""
    return config.get('defaults', {})


def merge_with_defaults(data: dict, defaults: dict) -> dict:
    """Merge scraper data with defaults."""
    result = dict(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # Merge nested dicts
            result[key] = {**result[key], **value}
        else:
            result[key] = value

    # Flatten rate_limiting for template access
    rate_limiting = result.get('rate_limiting', {})
    if isinstance(rate_limiting, dict):
        result['rate_delay'] = rate_limiting.get('delay', '1.5-3s')
        result['rate_notes'] = rate_limiting.get('notes', '')
        result['rate_max_requests'] = rate_limiting.get('max_requests', '')

    # Provide defaults for commonly missing fields
    if not result.get('schedule'):
        result['schedule'] = 'Not scheduled. Run manually or add to Node-RED.'
    if not result.get('source_url'):
        # Try to build from sources list
        sources = result.get('sources', [])
        if sources:
            result['source_url'] = ', '.join(s.get('url', '') for s in sources if s.get('url'))
        else:
            result['source_url'] = 'N/A'
    if not result.get('output_path'):
        result['output_path'] = 'See base_path/output/'
    if not result.get('main_script'):
        result['main_script'] = 'scraper.py'

    return result


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

    # Handle nested dict access (e.g., {{ rate_limiting.delay }})
    nested_pattern = r'\{\{\s*(\w+)\.(\w+)\s*\}\}'

    def replace_nested(match):
        parent = match.group(1)
        child = match.group(2)
        parent_val = data.get(parent, {})
        if isinstance(parent_val, dict):
            return str(parent_val.get(child, ''))
        return ''

    result = re.sub(nested_pattern, replace_nested, result)

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
            if isinstance(item, dict):
                # Handle dict items with nested access
                item_body = body
                for k, v in item.items():
                    item_body = item_body.replace('{{ ' + item_var + '.' + k + ' }}', str(v))
                item_body = item_body.strip()
            else:
                item_body = body.replace('{{ ' + item_var + ' }}', str(item))
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

    # Handle else conditions
    # Pattern: {% if var %} ... {% else %} ... {% endif %}
    if_else_pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}'

    def replace_if_else(match):
        var_name = match.group(1)
        if_body = match.group(2)
        else_body = match.group(3)

        value = data.get(var_name)
        if value:
            return if_body.strip()
        return else_body.strip()

    result = re.sub(if_else_pattern, replace_if_else, result, flags=re.DOTALL)

    # Clean up multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result


def get_output_path(scraper_id: str, data: dict) -> Path:
    """Get the path where CLAUDE.md should be written."""
    base_path = data.get('base_path', '')
    if base_path:
        return Path(base_path) / "CLAUDE.md"
    return BASE_DIR / scraper_id / "CLAUDE.md"


def generate_scraper_file(scraper_id: str, data: dict, template: str,
                          defaults: dict, dry_run: bool = False) -> str:
    """Generate CLAUDE.md for a single scraper."""
    # Merge with defaults
    merged_data = merge_with_defaults(data, defaults)

    output_path = get_output_path(scraper_id, merged_data)

    rendered = render_template(template, merged_data)

    if dry_run:
        return rendered

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered)

    return rendered


def generate_all(dry_run: bool = False, scraper_type: Optional[str] = None) -> None:
    """Generate all scraper files."""
    config = load_yaml()
    template = load_template()
    defaults = get_defaults(config)

    scrapers = config.get('scrapers', {})

    # Filter by type if specified
    if scraper_type:
        scrapers = {k: v for k, v in scrapers.items()
                    if v.get('type') == scraper_type}

    print(f"Generating {len(scrapers)} scraper files...")

    for scraper_id, data in scrapers.items():
        output_path = get_output_path(scraper_id, data)
        generate_scraper_file(scraper_id, data, template, defaults, dry_run)
        print(f"  Generated: {output_path}")

    print(f"\nDone. {len(scrapers)} files generated.")


def extract_from_existing() -> dict:
    """Extract data from existing CLAUDE.md files to YAML format."""
    scrapers = {}

    # Find all CLAUDE.md files in scrapers directory
    for claude_path in BASE_DIR.rglob("CLAUDE.md"):
        # Skip the root CLAUDE.md and template
        if claude_path.parent == BASE_DIR:
            continue
        if "TEMPLATE" in str(claude_path):
            continue

        with open(claude_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract scraper ID from path
        rel_path = claude_path.relative_to(BASE_DIR)
        scraper_id = str(rel_path.parent).replace('/', '_').upper()

        data = {
            'base_path': str(claude_path.parent),
            'status': 'active'
        }

        # Extract name from title
        title_match = re.search(r'^#\s+(.+?)(?:\s+Scraper|\s+-|\n)', content, re.MULTILINE)
        if title_match:
            data['name'] = title_match.group(1).strip()

        # Extract status from table
        status_match = re.search(r'\|\s*scraper\s*\|\s*(\w+)\s*\|', content)
        if status_match:
            data['status'] = status_match.group(1).strip()

        # Extract purpose
        purpose_match = re.search(r'## Purpose\s*\n+(.+?)(?:\n\n|\n##)', content, re.DOTALL)
        if purpose_match:
            purpose_text = purpose_match.group(1).strip()
            # Get first line or sentence
            first_line = purpose_text.split('\n')[0].strip()
            if first_line and not first_line.startswith('{TODO'):
                data['purpose'] = first_line

        # Extract source URLs
        source_match = re.search(r'\*\*(?:URL|Site|Sources?):\*\*\s*(.+)', content)
        if source_match:
            data['source_url'] = source_match.group(1).strip()

        # Extract schedule
        schedule_match = re.search(r'## (?:Schedule|Cron)\s*\n+(.+?)(?:\n\n|\n##)', content, re.DOTALL)
        if schedule_match:
            schedule_text = schedule_match.group(1).strip().split('\n')[0]
            if schedule_text and 'TODO' not in schedule_text:
                data['schedule'] = schedule_text

        # Extract output path
        output_match = re.search(r'(?:Output|OUTPUT)[:\s]+`?([^`\n]+\.csv)`?', content)
        if output_match:
            data['output_path'] = output_match.group(1).strip()

        # Determine type based on path
        if 'EUROPE/EUROPE' in str(claude_path):
            data['type'] = 'country'
        elif 'ROMANIA' in str(claude_path):
            data['type'] = 'data_source'
            data['code'] = 'RO'
        elif 'SOCIAL' in str(claude_path):
            data['type'] = 'social'
        else:
            data['type'] = 'country'

        scrapers[scraper_id] = data

    return {'scrapers': scrapers}


def validate_yaml() -> bool:
    """Validate YAML data completeness."""
    config = load_yaml()
    scrapers = config.get('scrapers', {})

    required_fields = ['name', 'type', 'status', 'base_path']
    errors = []
    warnings = []

    for scraper_id, data in scrapers.items():
        # Check required fields
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"{scraper_id}: Missing required field '{field}'")

        # Check optional fields
        if not data.get('purpose'):
            warnings.append(f"{scraper_id}: No purpose defined")

        if not data.get('main_script'):
            warnings.append(f"{scraper_id}: No main_script defined")

        # Verify base_path exists
        base_path = data.get('base_path', '')
        if base_path and not Path(base_path).exists():
            warnings.append(f"{scraper_id}: base_path does not exist: {base_path}")

    print(f"Validated {len(scrapers)} scrapers\n")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("\nWARNINGS:")
        for w in warnings[:20]:  # Limit warnings shown
            print(f"  - {w}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more warnings")

    if not errors and not warnings:
        print("All scrapers valid!")

    return len(errors) == 0


def show_diff(scraper_id: str) -> None:
    """Show diff between current and generated file."""
    config = load_yaml()
    template = load_template()
    defaults = get_defaults(config)

    scrapers = config.get('scrapers', {})
    scraper_id = scraper_id.upper()

    if scraper_id not in scrapers:
        print(f"ERROR: Scraper '{scraper_id}' not found in YAML")
        return

    data = scrapers[scraper_id]
    merged_data = merge_with_defaults(data, defaults)
    new_content = generate_scraper_file(scraper_id, merged_data, template, defaults, dry_run=True)

    current_path = get_output_path(scraper_id, data)
    if current_path.exists():
        with open(current_path, 'r', encoding='utf-8') as f:
            current_content = f.read()
    else:
        current_content = ""

    if current_content == new_content:
        print(f"{scraper_id}: No changes")
    else:
        print(f"{scraper_id}: Changes detected")
        print(f"\n--- Current ({current_path}) ---")
        print(current_content[:800] + "..." if len(current_content) > 800 else current_content)
        print("\n--- Generated ---")
        print(new_content[:800] + "..." if len(new_content) > 800 else new_content)


def show_status() -> None:
    """Show summary of all scrapers."""
    config = load_yaml()
    scrapers = config.get('scrapers', {})

    # Group by type
    types = {}
    for scraper_id, data in scrapers.items():
        scraper_type = data.get('type', 'unknown')
        if scraper_type not in types:
            types[scraper_type] = []
        status = data.get('status', 'unknown')
        name = data.get('name', scraper_id)
        types[scraper_type].append((scraper_id, name, status))

    print(f"Scraper Consolidator Summary: {len(scrapers)} total\n")

    for scraper_type in sorted(types.keys()):
        print(f"{scraper_type.upper()} ({len(types[scraper_type])}):")
        for scraper_id, name, status in sorted(types[scraper_type], key=lambda x: x[0]):
            status_icon = "[OK]" if status == "active" else "[--]"
            print(f"  {status_icon} {scraper_id}: {name}")
        print()

    # Files status
    print("File Status:")
    existing = 0
    missing = 0
    for scraper_id, data in scrapers.items():
        path = get_output_path(scraper_id, data)
        if path.exists():
            existing += 1
        else:
            missing += 1

    print(f"  Existing CLAUDE.md: {existing}")
    print(f"  Missing CLAUDE.md: {missing}")

    # Show YAML and template paths
    print(f"\nConfiguration:")
    print(f"  YAML: {YAML_PATH}")
    print(f"  Template: {TEMPLATE_PATH}")


def list_scrapers(scraper_type: Optional[str] = None,
                  status_filter: Optional[str] = None,
                  verbose: bool = False) -> None:
    """List all scrapers with optional filtering."""
    config = load_yaml()
    scrapers = config.get('scrapers', {})

    # Apply filters
    filtered = scrapers
    if scraper_type:
        filtered = {k: v for k, v in filtered.items()
                    if v.get('type') == scraper_type}
    if status_filter:
        filtered = {k: v for k, v in filtered.items()
                    if v.get('status') == status_filter}

    print(f"Scrapers: {len(filtered)} found\n")

    if verbose:
        for scraper_id, data in sorted(filtered.items()):
            print(f"{scraper_id}:")
            print(f"  Name: {data.get('name', 'N/A')}")
            print(f"  Type: {data.get('type', 'N/A')}")
            print(f"  Status: {data.get('status', 'N/A')}")
            print(f"  Path: {data.get('base_path', 'N/A')}")
            if data.get('schedule'):
                print(f"  Schedule: {data['schedule']}")
            print()
    else:
        # Table format
        print(f"{'ID':<25} {'NAME':<30} {'TYPE':<15} {'STATUS':<10}")
        print("-" * 80)
        for scraper_id, data in sorted(filtered.items()):
            name = data.get('name', 'N/A')[:28]
            scraper_type = data.get('type', 'N/A')
            status = data.get('status', 'N/A')
            print(f"{scraper_id:<25} {name:<30} {scraper_type:<15} {status:<10}")


def main():
    parser = argparse.ArgumentParser(description='Scraper CLAUDE.md Consolidator')
    parser.add_argument('--generate-all', action='store_true',
                        help='Regenerate all scraper files')
    parser.add_argument('--generate', metavar='ID',
                        help='Regenerate single scraper file')
    parser.add_argument('--extract', action='store_true',
                        help='Extract data from existing files to stdout')
    parser.add_argument('--validate', action='store_true',
                        help='Validate YAML data')
    parser.add_argument('--diff', metavar='ID',
                        help='Show diff for scraper')
    parser.add_argument('--status', action='store_true',
                        help='Show summary')
    parser.add_argument('--list', action='store_true',
                        help='List all scrapers')
    parser.add_argument('--type', metavar='TYPE',
                        help='Filter by type (country, data_source, multi_country, social)')
    parser.add_argument('--active', action='store_true',
                        help='Filter to active scrapers only')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing files')

    args = parser.parse_args()

    if args.generate_all:
        generate_all(args.dry_run, args.type)
    elif args.generate:
        config = load_yaml()
        template = load_template()
        defaults = get_defaults(config)
        scrapers = config.get('scrapers', {})

        scraper_id = args.generate.upper()
        if scraper_id not in scrapers:
            print(f"ERROR: Scraper '{scraper_id}' not found in YAML")
            sys.exit(1)

        data = scrapers[scraper_id]
        result = generate_scraper_file(scraper_id, data, template, defaults, args.dry_run)

        if args.dry_run:
            print(result)
        else:
            output_path = get_output_path(scraper_id, data)
            print(f"Generated: {output_path}")
    elif args.extract:
        extracted = extract_from_existing()
        print(yaml.dump(extracted, default_flow_style=False, allow_unicode=True, sort_keys=False))
    elif args.validate:
        success = validate_yaml()
        sys.exit(0 if success else 1)
    elif args.diff:
        show_diff(args.diff)
    elif args.status:
        show_status()
    elif args.list:
        status_filter = 'active' if args.active else None
        list_scrapers(args.type, status_filter, args.verbose)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
