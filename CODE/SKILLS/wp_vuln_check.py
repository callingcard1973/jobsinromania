#!/usr/bin/env python3
"""
WordPress Vulnerability Checker
Checks plugins/themes against WPScan API for known vulnerabilities.

Requires: WPSCAN_API_TOKEN environment variable
Free tier: 25 API requests/day
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.END}"


WPSCAN_API_BASE = "https://wpscan.com/api/v3"


def get_api_token() -> Optional[str]:
    """Get WPScan API token from environment"""
    return os.environ.get('WPSCAN_API_TOKEN')


def wpscan_api_request(endpoint: str, api_token: str) -> Optional[dict]:
    """Make request to WPScan API"""
    url = f"{WPSCAN_API_BASE}/{endpoint}"

    try:
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Token token={api_token}')
        req.add_header('User-Agent', 'WordPress Vulnerability Checker')

        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"{color('Error:', Colors.RED)} Invalid API token")
        elif e.code == 429:
            print(f"{color('Error:', Colors.RED)} API rate limit exceeded (25/day for free tier)")
        elif e.code == 404:
            return None  # Plugin/theme not found
        else:
            print(f"{color('Error:', Colors.RED)} API error: {e.code}")
        return None
    except Exception as e:
        print(f"{color('Error:', Colors.RED)} {str(e)}")
        return None


def parse_plugin_header(file_path: Path) -> Optional[dict]:
    """Parse plugin header to get name and version"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(8192)  # Read first 8KB

            # Look for plugin header
            name_match = re.search(r'Plugin Name:\s*(.+)', content)
            version_match = re.search(r'Version:\s*([\d.]+)', content)

            if name_match:
                return {
                    'name': name_match.group(1).strip(),
                    'version': version_match.group(1).strip() if version_match else None,
                    'slug': file_path.parent.name
                }
    except Exception:
        pass
    return None


def parse_theme_header(file_path: Path) -> Optional[dict]:
    """Parse theme style.css header"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(8192)

            name_match = re.search(r'Theme Name:\s*(.+)', content)
            version_match = re.search(r'Version:\s*([\d.]+)', content)

            if name_match:
                return {
                    'name': name_match.group(1).strip(),
                    'version': version_match.group(1).strip() if version_match else None,
                    'slug': file_path.parent.name
                }
    except Exception:
        pass
    return None


def find_plugins(wp_path: Path) -> list:
    """Find all plugins in wp-content/plugins"""
    plugins = []
    plugins_dir = wp_path / 'wp-content' / 'plugins'

    if not plugins_dir.exists():
        return plugins

    for plugin_dir in plugins_dir.iterdir():
        if plugin_dir.is_dir():
            # Look for main plugin file
            for php_file in plugin_dir.glob('*.php'):
                info = parse_plugin_header(php_file)
                if info:
                    plugins.append(info)
                    break

    return plugins


def find_themes(wp_path: Path) -> list:
    """Find all themes in wp-content/themes"""
    themes = []
    themes_dir = wp_path / 'wp-content' / 'themes'

    if not themes_dir.exists():
        return themes

    for theme_dir in themes_dir.iterdir():
        if theme_dir.is_dir():
            style_css = theme_dir / 'style.css'
            if style_css.exists():
                info = parse_theme_header(style_css)
                if info:
                    themes.append(info)

    return themes


def get_wp_version(wp_path: Path) -> Optional[str]:
    """Get WordPress version from wp-includes/version.php"""
    version_file = wp_path / 'wp-includes' / 'version.php'

    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                content = f.read()
                match = re.search(r"\\\$wp_version\s*=\s*['\"]([^'\"]+)['\"]", content)
                if match:
                    return match.group(1)
        except Exception:
            pass
    return None


def check_wordpress_version(version: str, api_token: str) -> list:
    """Check WordPress core for vulnerabilities"""
    data = wpscan_api_request(f"wordpresses/{version.replace('.', '')}", api_token)

    if data and version.replace('.', '') in data:
        return data[version.replace('.', '')].get('vulnerabilities', [])
    return []


def check_plugin(slug: str, version: str, api_token: str) -> list:
    """Check plugin for vulnerabilities"""
    data = wpscan_api_request(f"plugins/{slug}", api_token)

    if not data or slug not in data:
        return []

    vulns = data[slug].get('vulnerabilities', [])

    # Filter by version if provided
    if version:
        filtered = []
        for vuln in vulns:
            fixed_in = vuln.get('fixed_in')
            if fixed_in is None or version_compare(version, fixed_in) < 0:
                filtered.append(vuln)
        return filtered

    return vulns


def check_theme(slug: str, version: str, api_token: str) -> list:
    """Check theme for vulnerabilities"""
    data = wpscan_api_request(f"themes/{slug}", api_token)

    if not data or slug not in data:
        return []

    vulns = data[slug].get('vulnerabilities', [])

    if version:
        filtered = []
        for vuln in vulns:
            fixed_in = vuln.get('fixed_in')
            if fixed_in is None or version_compare(version, fixed_in) < 0:
                filtered.append(vuln)
        return filtered

    return vulns


def version_compare(v1: str, v2: str) -> int:
    """Compare version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
    def normalize(v):
        return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.') if x]

    parts1 = normalize(v1)
    parts2 = normalize(v2)

    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 < p2:
            return -1
        if p1 > p2:
            return 1
    return 0


def print_vulnerabilities(vulns: list, component: str, version: str):
    """Print vulnerability details"""
    if not vulns:
        print(f"  {color('[PASS]', Colors.GREEN)} No known vulnerabilities")
        return

    for vuln in vulns:
        severity = vuln.get('cvss', {}).get('score', 'N/A')
        title = vuln.get('title', 'Unknown')
        fixed_in = vuln.get('fixed_in', 'Not fixed')

        if isinstance(severity, (int, float)) and severity >= 7:
            sev_color = Colors.RED
            sev_label = 'HIGH'
        elif isinstance(severity, (int, float)) and severity >= 4:
            sev_color = Colors.YELLOW
            sev_label = 'MEDIUM'
        else:
            sev_color = Colors.BLUE
            sev_label = 'LOW'

        print(f"  {color(f'[{sev_label}]', sev_color)} {title}")
        print(f"       CVSS: {severity}")
        print(f"       Fixed in: {fixed_in}")

        refs = vuln.get('references', {})
        if 'cve' in refs:
            print(f"       CVE: {', '.join(refs['cve'])}")
        print()


def main():
    parser = argparse.ArgumentParser(description='WordPress Vulnerability Checker')
    parser.add_argument('path', nargs='?', default='.', help='Path to WordPress installation')
    parser.add_argument('--plugin', help='Check specific plugin by slug')
    parser.add_argument('--theme', help='Check specific theme by slug')
    parser.add_argument('--version', help='Version to check (with --plugin or --theme)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    api_token = get_api_token()
    if not api_token:
        print(f"{color('Error:', Colors.RED)} WPSCAN_API_TOKEN environment variable not set")
        print("Get a free API token at: https://wpscan.com/api")
        print("Usage: export WPSCAN_API_TOKEN=your_token")
        sys.exit(1)

    results = {
        'wordpress': {'version': None, 'vulnerabilities': []},
        'plugins': [],
        'themes': []
    }

    # Check specific plugin/theme
    if args.plugin:
        print(f"Checking plugin: {args.plugin}")
        vulns = check_plugin(args.plugin, args.version or '', api_token)
        if args.json:
            print(json.dumps({'plugin': args.plugin, 'version': args.version, 'vulnerabilities': vulns}, indent=2))
        else:
            print_vulnerabilities(vulns, args.plugin, args.version or 'unknown')
        sys.exit(0)

    if args.theme:
        print(f"Checking theme: {args.theme}")
        vulns = check_theme(args.theme, args.version or '', api_token)
        if args.json:
            print(json.dumps({'theme': args.theme, 'version': args.version, 'vulnerabilities': vulns}, indent=2))
        else:
            print_vulnerabilities(vulns, args.theme, args.version or 'unknown')
        sys.exit(0)

    # Scan WordPress installation
    wp_path = Path(args.path)

    if not (wp_path / 'wp-config.php').exists() and not (wp_path / 'wp-content').exists():
        print(f"{color('Error:', Colors.RED)} Not a WordPress installation: {wp_path}")
        sys.exit(1)

    print(f"{color('WordPress Vulnerability Scan', Colors.BOLD)}")
    print(f"Path: {wp_path.absolute()}")
    print()

    # Check WordPress core
    wp_version = get_wp_version(wp_path)
    if wp_version:
        print(f"{color('## WordPress Core', Colors.BOLD)} (v{wp_version})")
        vulns = check_wordpress_version(wp_version, api_token)
        results['wordpress']['version'] = wp_version
        results['wordpress']['vulnerabilities'] = vulns
        print_vulnerabilities(vulns, 'WordPress', wp_version)
        print()

    # Find and check plugins
    plugins = find_plugins(wp_path)
    print(f"{color('## Plugins', Colors.BOLD)} ({len(plugins)} found)")

    for plugin in plugins:
        print(f"\n  {color(plugin['name'], Colors.BOLD)} (v{plugin['version'] or 'unknown'})")
        vulns = check_plugin(plugin['slug'], plugin['version'] or '', api_token)
        plugin['vulnerabilities'] = vulns
        results['plugins'].append(plugin)

        if vulns:
            for vuln in vulns[:3]:  # Show first 3
                severity = vuln.get('cvss', {}).get('score', 'N/A')
                print(f"    {color('[VULN]', Colors.RED)} {vuln.get('title', 'Unknown')[:60]}")
        else:
            print(f"    {color('[OK]', Colors.GREEN)} No known vulnerabilities")

    print()

    # Find and check themes
    themes = find_themes(wp_path)
    print(f"{color('## Themes', Colors.BOLD)} ({len(themes)} found)")

    for theme in themes:
        print(f"\n  {color(theme['name'], Colors.BOLD)} (v{theme['version'] or 'unknown'})")
        vulns = check_theme(theme['slug'], theme['version'] or '', api_token)
        theme['vulnerabilities'] = vulns
        results['themes'].append(theme)

        if vulns:
            for vuln in vulns[:3]:
                print(f"    {color('[VULN]', Colors.RED)} {vuln.get('title', 'Unknown')[:60]}")
        else:
            print(f"    {color('[OK]', Colors.GREEN)} No known vulnerabilities")

    print()

    # Summary
    total_vulns = (
        len(results['wordpress']['vulnerabilities']) +
        sum(len(p.get('vulnerabilities', [])) for p in results['plugins']) +
        sum(len(t.get('vulnerabilities', [])) for t in results['themes'])
    )

    print(f"{color('## Summary', Colors.BOLD)}")
    print(f"  Total vulnerabilities found: {color(str(total_vulns), Colors.RED if total_vulns else Colors.GREEN)}")
    print(f"  Plugins checked: {len(plugins)}")
    print(f"  Themes checked: {len(themes)}")

    if args.json:
        print(json.dumps(results, indent=2))

    sys.exit(1 if total_vulns else 0)


if __name__ == "__main__":
    main()
