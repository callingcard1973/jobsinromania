#!/usr/bin/env python3
"""
WordPress Site Health Checker
Performs external security and performance checks on WordPress sites.
"""

import argparse
import json
import re
import socket
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.END}"


def fetch_url(url: str, timeout: int = 10, method: str = "GET") -> tuple[Optional[bytes], dict, int, Optional[str]]:
    """Fetch URL and return (body, headers, status_code, error)"""
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('User-Agent', 'Mozilla/5.0 (WordPress Site Checker)')

        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return response.read(), dict(response.headers), response.status, None
    except urllib.error.HTTPError as e:
        return None, dict(e.headers) if hasattr(e, 'headers') else {}, e.code, str(e)
    except urllib.error.URLError as e:
        return None, {}, 0, str(e.reason)
    except Exception as e:
        return None, {}, 0, str(e)


def check_ssl(hostname: str) -> dict:
    """Check SSL certificate validity and details"""
    result = {"status": "unknown", "details": {}}

    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                # Parse expiry
                expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                days_left = (expires - datetime.now()).days

                result["details"] = {
                    "issuer": dict(x[0] for x in cert.get('issuer', [])).get('organizationName', 'Unknown'),
                    "expires": cert['notAfter'],
                    "days_left": days_left,
                    "subject": dict(x[0] for x in cert.get('subject', [])).get('commonName', 'Unknown'),
                }

                if days_left < 0:
                    result["status"] = "expired"
                elif days_left < 30:
                    result["status"] = "expiring_soon"
                else:
                    result["status"] = "valid"

    except ssl.SSLError as e:
        result["status"] = "invalid"
        result["details"]["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)

    return result


def check_security_headers(headers: dict) -> dict:
    """Check for important security headers"""
    checks = {
        "X-Frame-Options": {
            "present": False,
            "value": None,
            "severity": "warning",
            "recommendation": "Add 'X-Frame-Options: SAMEORIGIN' to prevent clickjacking"
        },
        "X-Content-Type-Options": {
            "present": False,
            "value": None,
            "severity": "warning",
            "recommendation": "Add 'X-Content-Type-Options: nosniff' to prevent MIME sniffing"
        },
        "Strict-Transport-Security": {
            "present": False,
            "value": None,
            "severity": "warning",
            "recommendation": "Add HSTS header to enforce HTTPS"
        },
        "Content-Security-Policy": {
            "present": False,
            "value": None,
            "severity": "info",
            "recommendation": "Consider adding CSP to prevent XSS attacks"
        },
        "X-XSS-Protection": {
            "present": False,
            "value": None,
            "severity": "info",
            "recommendation": "Add 'X-XSS-Protection: 1; mode=block' (legacy but still useful)"
        },
        "Referrer-Policy": {
            "present": False,
            "value": None,
            "severity": "info",
            "recommendation": "Add Referrer-Policy to control referrer information"
        },
        "Permissions-Policy": {
            "present": False,
            "value": None,
            "severity": "info",
            "recommendation": "Add Permissions-Policy to control browser features"
        }
    }

    # Normalize header names to lowercase for comparison
    headers_lower = {k.lower(): v for k, v in headers.items()}

    for header in checks:
        header_lower = header.lower()
        if header_lower in headers_lower:
            checks[header]["present"] = True
            checks[header]["value"] = headers_lower[header_lower]

    return checks


def check_wordpress_version(body: bytes, headers: dict) -> dict:
    """Detect WordPress version from various sources"""
    result = {"detected": False, "version": None, "source": None}

    if not body:
        return result

    html = body.decode('utf-8', errors='ignore')

    # Check meta generator tag
    meta_match = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress\s*([\d.]+)?["\']', html, re.I)
    if meta_match:
        result["detected"] = True
        result["version"] = meta_match.group(1)
        result["source"] = "meta_generator"
        return result

    # Check for WordPress in HTML
    if 'wp-content' in html or 'wp-includes' in html:
        result["detected"] = True
        result["source"] = "wp_paths"

    # Check for version in CSS/JS links
    version_match = re.search(r'[?&]ver=([\d.]+)', html)
    if version_match and result["detected"]:
        result["version"] = version_match.group(1)
        result["source"] = "asset_version"

    return result


def check_exposed_files(base_url: str) -> list:
    """Check for exposed sensitive files"""
    exposed = []

    sensitive_paths = [
        ("/wp-config.php.bak", "critical", "Backup of wp-config with DB credentials"),
        ("/wp-config.php~", "critical", "Editor backup of wp-config"),
        ("/wp-config.php.old", "critical", "Old wp-config file"),
        ("/wp-config.php.save", "critical", "Saved wp-config file"),
        ("/.git/config", "critical", "Git repository exposed"),
        ("/.env", "critical", "Environment file with secrets"),
        ("/debug.log", "warning", "Debug log may contain sensitive info"),
        ("/wp-content/debug.log", "warning", "WordPress debug log"),
        ("/error_log", "warning", "Error log exposed"),
        ("/php_errors.log", "warning", "PHP error log"),
        ("/.htaccess", "info", ".htaccess readable"),
        ("/readme.html", "info", "WordPress readme (version disclosure)"),
        ("/license.txt", "info", "License file (version disclosure)"),
        ("/wp-admin/install.php", "warning", "Install script accessible"),
        ("/wp-includes/version.php", "info", "Version file (may be blocked)"),
    ]

    for path, severity, description in sensitive_paths:
        url = base_url.rstrip('/') + path
        body, headers, status, error = fetch_url(url, timeout=5, method="HEAD")

        if status == 200:
            exposed.append({
                "path": path,
                "severity": severity,
                "description": description,
                "status": status
            })

    return exposed


def check_xmlrpc(base_url: str) -> dict:
    """Check if XML-RPC is enabled"""
    url = base_url.rstrip('/') + '/xmlrpc.php'
    body, headers, status, error = fetch_url(url, timeout=5)

    result = {
        "enabled": False,
        "status": status,
        "severity": "info"
    }

    if status == 200:
        result["enabled"] = True
        result["severity"] = "warning"
        result["recommendation"] = "Disable XML-RPC to prevent brute force and DDoS attacks"
    elif status == 405:  # Method not allowed but endpoint exists
        result["enabled"] = True
        result["severity"] = "info"
        result["recommendation"] = "XML-RPC exists but may be partially protected"

    return result


def check_rest_api(base_url: str) -> dict:
    """Check REST API exposure"""
    url = base_url.rstrip('/') + '/wp-json/'
    body, headers, status, error = fetch_url(url, timeout=5)

    result = {
        "enabled": False,
        "user_enumeration": False,
        "namespaces": []
    }

    if status == 200 and body:
        result["enabled"] = True
        try:
            data = json.loads(body)
            result["namespaces"] = data.get("namespaces", [])
        except json.JSONDecodeError:
            pass

        # Check user enumeration
        users_url = base_url.rstrip('/') + '/wp-json/wp/v2/users'
        users_body, _, users_status, _ = fetch_url(users_url, timeout=5)
        if users_status == 200 and users_body:
            result["user_enumeration"] = True
            result["severity"] = "warning"
            result["recommendation"] = "Disable user enumeration via REST API"

    return result


def check_login_page(base_url: str) -> dict:
    """Check login page accessibility"""
    result = {
        "wp_login_accessible": False,
        "wp_admin_redirect": False
    }

    # Check wp-login.php
    login_url = base_url.rstrip('/') + '/wp-login.php'
    body, headers, status, error = fetch_url(login_url, timeout=5)
    if status == 200:
        result["wp_login_accessible"] = True

    # Check wp-admin redirect
    admin_url = base_url.rstrip('/') + '/wp-admin/'
    body, headers, status, error = fetch_url(admin_url, timeout=5)
    if status in [200, 302, 301]:
        result["wp_admin_redirect"] = True

    return result


def check_robots_txt(base_url: str) -> dict:
    """Check robots.txt for sensitive paths"""
    url = base_url.rstrip('/') + '/robots.txt'
    body, headers, status, error = fetch_url(url, timeout=5)

    result = {
        "exists": False,
        "content": None,
        "sensitive_paths_blocked": [],
        "issues": []
    }

    if status == 200 and body:
        result["exists"] = True
        content = body.decode('utf-8', errors='ignore')
        result["content"] = content[:1000]  # First 1000 chars

        # Check for sensitive paths
        sensitive = ['/wp-admin', '/wp-includes', '/wp-content/plugins', '/wp-content/uploads']
        for path in sensitive:
            if f'Disallow: {path}' in content:
                result["sensitive_paths_blocked"].append(path)

        # Check for sitemap
        if 'sitemap' not in content.lower():
            result["issues"].append("No sitemap reference in robots.txt")

    return result


def measure_response_time(url: str) -> dict:
    """Measure response time"""
    import time

    result = {"ttfb": None, "total": None}

    try:
        start = time.time()
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (WordPress Site Checker)')

        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            first_byte = time.time()
            response.read()
            end = time.time()

            result["ttfb"] = round((first_byte - start) * 1000)  # ms
            result["total"] = round((end - start) * 1000)  # ms
    except Exception as e:
        result["error"] = str(e)

    return result


def print_report(url: str, results: dict):
    """Print formatted report"""
    print(f"\n{color('='*60, Colors.BLUE)}")
    print(f"{color('WordPress Site Health Report', Colors.BOLD)}")
    print(f"URL: {url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{color('='*60, Colors.BLUE)}\n")

    # SSL
    print(f"{color('## SSL/HTTPS', Colors.BOLD)}")
    ssl_status = results.get("ssl", {})
    if ssl_status.get("status") == "valid":
        print(f"  {color('[PASS]', Colors.GREEN)} SSL Certificate Valid")
        print(f"       Expires: {ssl_status['details'].get('expires')} ({ssl_status['details'].get('days_left')} days)")
        print(f"       Issuer: {ssl_status['details'].get('issuer')}")
    elif ssl_status.get("status") == "expiring_soon":
        print(f"  {color('[WARN]', Colors.YELLOW)} SSL Certificate Expiring Soon")
        print(f"       Days left: {ssl_status['details'].get('days_left')}")
    else:
        print(f"  {color('[FAIL]', Colors.RED)} SSL Certificate Issue: {ssl_status.get('status')}")
    print()

    # Response Time
    print(f"{color('## Performance', Colors.BOLD)}")
    timing = results.get("response_time", {})
    if timing.get("ttfb"):
        ttfb = timing["ttfb"]
        ttfb_color = Colors.GREEN if ttfb < 200 else Colors.YELLOW if ttfb < 600 else Colors.RED
        print(f"  TTFB: {color(f'{ttfb}ms', ttfb_color)}")
        print(f"  Total: {timing['total']}ms")
    print()

    # WordPress Detection
    print(f"{color('## WordPress Detection', Colors.BOLD)}")
    wp = results.get("wordpress", {})
    if wp.get("detected"):
        version = wp.get("version") or "Unknown"
        print(f"  {color('[INFO]', Colors.BLUE)} WordPress Detected")
        print(f"       Version: {version}")
        print(f"       Source: {wp.get('source')}")
    else:
        print(f"  {color('[INFO]', Colors.BLUE)} WordPress not detected (or well hidden)")
    print()

    # Security Headers
    print(f"{color('## Security Headers', Colors.BOLD)}")
    headers = results.get("security_headers", {})
    for header, info in headers.items():
        if info["present"]:
            print(f"  {color('[PASS]', Colors.GREEN)} {header}: {info['value'][:50]}...")
        else:
            severity_color = Colors.YELLOW if info["severity"] == "warning" else Colors.BLUE
            print(f"  {color('[MISS]', severity_color)} {header}")
            print(f"       {info['recommendation']}")
    print()

    # Exposed Files
    print(f"{color('## Exposed Files', Colors.BOLD)}")
    exposed = results.get("exposed_files", [])
    if exposed:
        for f in exposed:
            sev_color = Colors.RED if f["severity"] == "critical" else Colors.YELLOW
            print(f"  {color('[' + f['severity'].upper() + ']', sev_color)} {f['path']}")
            print(f"       {f['description']}")
    else:
        print(f"  {color('[PASS]', Colors.GREEN)} No exposed sensitive files detected")
    print()

    # XML-RPC
    print(f"{color('## XML-RPC', Colors.BOLD)}")
    xmlrpc = results.get("xmlrpc", {})
    if xmlrpc.get("enabled"):
        print(f"  {color('[WARN]', Colors.YELLOW)} XML-RPC is enabled")
        print(f"       {xmlrpc.get('recommendation', '')}")
    else:
        print(f"  {color('[PASS]', Colors.GREEN)} XML-RPC disabled or protected")
    print()

    # REST API
    print(f"{color('## REST API', Colors.BOLD)}")
    rest = results.get("rest_api", {})
    if rest.get("enabled"):
        print(f"  {color('[INFO]', Colors.BLUE)} REST API enabled")
        if rest.get("user_enumeration"):
            print(f"  {color('[WARN]', Colors.YELLOW)} User enumeration possible via /wp-json/wp/v2/users")
    else:
        print(f"  {color('[INFO]', Colors.BLUE)} REST API not detected")
    print()

    # Summary
    print(f"{color('## Summary', Colors.BOLD)}")
    critical = len([f for f in exposed if f["severity"] == "critical"])
    warnings = len([f for f in exposed if f["severity"] == "warning"])
    warnings += len([h for h, i in headers.items() if not i["present"] and i["severity"] == "warning"])
    if xmlrpc.get("severity") == "warning":
        warnings += 1
    if rest.get("user_enumeration"):
        warnings += 1

    print(f"  Critical Issues: {color(str(critical), Colors.RED if critical else Colors.GREEN)}")
    print(f"  Warnings: {color(str(warnings), Colors.YELLOW if warnings else Colors.GREEN)}")
    print()


def main():
    parser = argparse.ArgumentParser(description='WordPress Site Health Checker')
    parser.add_argument('url', help='WordPress site URL to check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--quick', action='store_true', help='Quick scan (skip exposed files check)')
    args = parser.parse_args()

    url = args.url
    if not url.startswith('http'):
        url = 'https://' + url

    parsed = urlparse(url)
    hostname = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Scanning {url}...")

    results = {}

    # SSL Check
    results["ssl"] = check_ssl(hostname)

    # Fetch main page
    body, headers, status, error = fetch_url(url)

    if error and status == 0:
        print(f"{color('Error:', Colors.RED)} Could not connect to {url}")
        print(f"  {error}")
        sys.exit(1)

    # Response time
    results["response_time"] = measure_response_time(url)

    # Security headers
    results["security_headers"] = check_security_headers(headers)

    # WordPress detection
    results["wordpress"] = check_wordpress_version(body, headers)

    # Exposed files (skip if --quick)
    if not args.quick:
        results["exposed_files"] = check_exposed_files(base_url)
    else:
        results["exposed_files"] = []

    # XML-RPC
    results["xmlrpc"] = check_xmlrpc(base_url)

    # REST API
    results["rest_api"] = check_rest_api(base_url)

    # Robots.txt
    results["robots"] = check_robots_txt(base_url)

    # Login page
    results["login"] = check_login_page(base_url)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(url, results)


if __name__ == "__main__":
    main()
