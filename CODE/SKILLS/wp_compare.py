#!/usr/bin/env python3
"""
WordPress Environment Comparison Tool
Compares staging vs production or two WordPress installations.
"""

import argparse
import json
import subprocess
import sys
import urllib.request
import urllib.error
import ssl
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.END}"


def fetch_url(url: str, timeout: int = 10):
    """Fetch URL content"""
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (WordPress Compare Tool)')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return response.read(), dict(response.headers), response.status
    except Exception as e:
        return None, {}, 0


def get_wp_version_from_url(url: str) -> Optional[str]:
    """Extract WordPress version from site"""
    body, _, _ = fetch_url(url)
    if not body:
        return None

    import re
    html = body.decode('utf-8', errors='ignore')

    # Check generator meta
    match = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress\s*([\d.]+)?["\']', html, re.I)
    if match:
        return match.group(1)

    return None


def get_plugins_from_url(url: str) -> List[str]:
    """Detect plugins from URL (limited - based on visible assets)"""
    body, _, _ = fetch_url(url)
    if not body:
        return []

    import re
    html = body.decode('utf-8', errors='ignore')

    plugins = set()
    # Find plugin references in wp-content/plugins/
    matches = re.findall(r'/wp-content/plugins/([^/]+)/', html)
    plugins.update(matches)

    return sorted(list(plugins))


def get_theme_from_url(url: str) -> Optional[str]:
    """Detect active theme from URL"""
    body, _, _ = fetch_url(url)
    if not body:
        return None

    import re
    html = body.decode('utf-8', errors='ignore')

    # Find theme references in wp-content/themes/
    match = re.search(r'/wp-content/themes/([^/]+)/', html)
    if match:
        return match.group(1)

    return None


def get_response_headers(url: str) -> Dict:
    """Get response headers for comparison"""
    _, headers, status = fetch_url(url)
    return {
        "status": status,
        "server": headers.get("Server", "Unknown"),
        "x-powered-by": headers.get("X-Powered-By", "Not exposed"),
        "cache-control": headers.get("Cache-Control", "Not set"),
        "content-encoding": headers.get("Content-Encoding", "None"),
    }


def measure_ttfb(url: str) -> int:
    """Measure Time to First Byte in ms"""
    import time
    try:
        start = time.time()
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            first_byte = time.time()
            return round((first_byte - start) * 1000)
    except:
        return -1


def compare_environments(url1: str, url2: str) -> Dict:
    """Compare two WordPress environments"""
    comparison = {
        "env1": {"url": url1},
        "env2": {"url": url2},
        "differences": [],
        "warnings": []
    }

    print(f"Comparing environments...")
    print(f"  Environment 1: {url1}")
    print(f"  Environment 2: {url2}\n")

    # WordPress versions
    print("Checking WordPress versions...")
    v1 = get_wp_version_from_url(url1)
    v2 = get_wp_version_from_url(url2)
    comparison["env1"]["wp_version"] = v1
    comparison["env2"]["wp_version"] = v2

    if v1 != v2:
        comparison["differences"].append({
            "type": "wp_version",
            "env1": v1,
            "env2": v2,
            "severity": "warning"
        })

    # Active themes
    print("Checking themes...")
    t1 = get_theme_from_url(url1)
    t2 = get_theme_from_url(url2)
    comparison["env1"]["theme"] = t1
    comparison["env2"]["theme"] = t2

    if t1 != t2:
        comparison["differences"].append({
            "type": "theme",
            "env1": t1,
            "env2": t2,
            "severity": "critical"
        })

    # Visible plugins
    print("Checking visible plugins...")
    p1 = set(get_plugins_from_url(url1))
    p2 = set(get_plugins_from_url(url2))
    comparison["env1"]["plugins"] = list(p1)
    comparison["env2"]["plugins"] = list(p2)

    only_in_1 = p1 - p2
    only_in_2 = p2 - p1

    if only_in_1:
        comparison["differences"].append({
            "type": "plugins_only_in_env1",
            "plugins": list(only_in_1),
            "severity": "warning"
        })

    if only_in_2:
        comparison["differences"].append({
            "type": "plugins_only_in_env2",
            "plugins": list(only_in_2),
            "severity": "warning"
        })

    # Response headers
    print("Checking response headers...")
    h1 = get_response_headers(url1)
    h2 = get_response_headers(url2)
    comparison["env1"]["headers"] = h1
    comparison["env2"]["headers"] = h2

    for key in h1:
        if h1[key] != h2[key]:
            comparison["differences"].append({
                "type": f"header_{key}",
                "env1": h1[key],
                "env2": h2[key],
                "severity": "info"
            })

    # Performance comparison
    print("Measuring performance...")
    ttfb1 = measure_ttfb(url1)
    ttfb2 = measure_ttfb(url2)
    comparison["env1"]["ttfb_ms"] = ttfb1
    comparison["env2"]["ttfb_ms"] = ttfb2

    if ttfb1 > 0 and ttfb2 > 0:
        diff_pct = abs(ttfb1 - ttfb2) / max(ttfb1, ttfb2) * 100
        if diff_pct > 50:
            comparison["differences"].append({
                "type": "performance",
                "env1": f"{ttfb1}ms",
                "env2": f"{ttfb2}ms",
                "difference_percent": round(diff_pct, 1),
                "severity": "warning"
            })

    # Robots.txt comparison
    print("Checking robots.txt...")
    r1, _, _ = fetch_url(url1.rstrip('/') + '/robots.txt')
    r2, _, _ = fetch_url(url2.rstrip('/') + '/robots.txt')

    if r1 and r2:
        if r1 != r2:
            comparison["differences"].append({
                "type": "robots_txt",
                "message": "robots.txt files differ",
                "severity": "warning"
            })

            # Check if staging is blocking search engines
            if r2 and b'Disallow: /' in r2:
                comparison["warnings"].append(
                    "Environment 2 has restrictive robots.txt (may be blocking search engines)"
                )

    return comparison


def print_comparison(comparison: Dict):
    """Print formatted comparison results"""
    print(f"\n{color('='*60, Colors.BLUE)}")
    print(f"{color('WordPress Environment Comparison', Colors.BOLD)}")
    print(f"{color('='*60, Colors.BLUE)}\n")

    # Summary table
    print(f"{'Property':<25} {'Env 1':<25} {'Env 2':<25}")
    print("-" * 75)

    e1 = comparison["env1"]
    e2 = comparison["env2"]

    rows = [
        ("URL", e1["url"][:23], e2["url"][:23]),
        ("WordPress Version", e1.get("wp_version", "Unknown"), e2.get("wp_version", "Unknown")),
        ("Theme", e1.get("theme", "Unknown"), e2.get("theme", "Unknown")),
        ("TTFB", f"{e1.get('ttfb_ms', 'N/A')}ms", f"{e2.get('ttfb_ms', 'N/A')}ms"),
        ("Server", e1.get("headers", {}).get("server", "Unknown")[:23],
         e2.get("headers", {}).get("server", "Unknown")[:23]),
    ]

    for label, v1, v2 in rows:
        match = v1 == v2
        v1_color = Colors.GREEN if match else Colors.YELLOW
        v2_color = Colors.GREEN if match else Colors.YELLOW
        print(f"{label:<25} {color(str(v1)[:23], v1_color):<35} {color(str(v2)[:23], v2_color):<35}")

    # Plugins
    print(f"\n{color('Plugins Detected:', Colors.BOLD)}")
    p1 = set(e1.get("plugins", []))
    p2 = set(e2.get("plugins", []))
    all_plugins = sorted(p1 | p2)

    for plugin in all_plugins[:15]:  # Limit output
        in_1 = "✓" if plugin in p1 else "✗"
        in_2 = "✓" if plugin in p2 else "✗"
        c1 = Colors.GREEN if plugin in p1 else Colors.RED
        c2 = Colors.GREEN if plugin in p2 else Colors.RED
        print(f"  {plugin:<35} {color(in_1, c1)}  {color(in_2, c2)}")

    if len(all_plugins) > 15:
        print(f"  ... and {len(all_plugins) - 15} more")

    # Differences
    if comparison["differences"]:
        print(f"\n{color('Differences Found:', Colors.BOLD)}")
        for diff in comparison["differences"]:
            sev = diff.get("severity", "info")
            sev_color = {"critical": Colors.RED, "warning": Colors.YELLOW, "info": Colors.BLUE}.get(sev, Colors.BLUE)
            print(f"  {color(f'[{sev.upper()}]', sev_color)} {diff['type']}")
            if "env1" in diff and "env2" in diff:
                print(f"       Env 1: {diff['env1']}")
                print(f"       Env 2: {diff['env2']}")
            if "plugins" in diff:
                print(f"       {', '.join(diff['plugins'])}")
            if "message" in diff:
                print(f"       {diff['message']}")

    # Warnings
    if comparison["warnings"]:
        print(f"\n{color('Warnings:', Colors.BOLD)}")
        for warning in comparison["warnings"]:
            print(f"  {color('⚠', Colors.YELLOW)} {warning}")

    # Summary
    print(f"\n{color('Summary:', Colors.BOLD)}")
    critical = len([d for d in comparison["differences"] if d.get("severity") == "critical"])
    warnings = len([d for d in comparison["differences"] if d.get("severity") == "warning"])
    print(f"  Critical differences: {color(str(critical), Colors.RED if critical else Colors.GREEN)}")
    print(f"  Warnings: {color(str(warnings), Colors.YELLOW if warnings else Colors.GREEN)}")

    if critical == 0 and warnings == 0:
        print(f"\n  {color('✓ Environments appear to be in sync!', Colors.GREEN)}")
    elif critical > 0:
        print(f"\n  {color('✗ Critical differences detected - review before deploying!', Colors.RED)}")


def compare_local_dirs(path1: str, path2: str) -> Dict:
    """Compare two local WordPress directories"""
    comparison = {
        "path1": path1,
        "path2": path2,
        "differences": [],
        "file_changes": {"added": [], "removed": [], "modified": []}
    }

    # Compare using diff if available
    try:
        result = subprocess.run(
            f"diff -rq {path1} {path2}",
            shell=True,
            capture_output=True,
            text=True
        )

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            if line.startswith('Only in ' + path1):
                comparison["file_changes"]["removed"].append(line)
            elif line.startswith('Only in ' + path2):
                comparison["file_changes"]["added"].append(line)
            elif 'differ' in line:
                comparison["file_changes"]["modified"].append(line)

    except Exception as e:
        comparison["error"] = str(e)

    return comparison


def main():
    parser = argparse.ArgumentParser(description='WordPress Environment Comparison Tool')
    parser.add_argument('env1', help='First environment (URL or path)')
    parser.add_argument('env2', help='Second environment (URL or path)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--local', action='store_true', help='Compare local directories instead of URLs')
    args = parser.parse_args()

    env1 = args.env1
    env2 = args.env2

    if args.local:
        # Compare local directories
        if not Path(env1).exists() or not Path(env2).exists():
            print(f"{color('Error:', Colors.RED)} One or both paths do not exist")
            sys.exit(1)

        comparison = compare_local_dirs(env1, env2)

        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print(f"\n{color('Local Directory Comparison', Colors.BOLD)}")
            print(f"Path 1: {env1}")
            print(f"Path 2: {env2}\n")

            changes = comparison["file_changes"]
            print(f"Added in Path 2: {len(changes['added'])} files")
            print(f"Removed from Path 2: {len(changes['removed'])} files")
            print(f"Modified: {len(changes['modified'])} files")

            if changes["modified"]:
                print(f"\n{color('Modified files:', Colors.YELLOW)}")
                for f in changes["modified"][:20]:
                    print(f"  {f}")
                if len(changes["modified"]) > 20:
                    print(f"  ... and {len(changes['modified']) - 20} more")

    else:
        # Compare URLs
        if not env1.startswith('http'):
            env1 = 'https://' + env1
        if not env2.startswith('http'):
            env2 = 'https://' + env2

        comparison = compare_environments(env1, env2)

        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print_comparison(comparison)


if __name__ == "__main__":
    main()
