#!/usr/bin/env python3
"""
WordPress Health Report Generator
Generates beautiful HTML reports combining all checks.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error
import ssl
import socket
import re


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Health Report - {site}</title>
    <style>
        :root {{
            --pass: #22c55e;
            --warn: #f59e0b;
            --fail: #ef4444;
            --info: #3b82f6;
            --bg: #0f172a;
            --card: #1e293b;
            --text: #e2e8f0;
            --muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 1rem;
        }}
        header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        header .meta {{ color: rgba(255,255,255,0.8); }}
        .score-card {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 2rem 0;
        }}
        .score {{
            text-align: center;
            padding: 1.5rem 2rem;
            background: var(--card);
            border-radius: 1rem;
            min-width: 150px;
        }}
        .score .number {{
            font-size: 3rem;
            font-weight: bold;
        }}
        .score .label {{ color: var(--muted); text-transform: uppercase; font-size: 0.75rem; }}
        .score.pass .number {{ color: var(--pass); }}
        .score.warn .number {{ color: var(--warn); }}
        .score.fail .number {{ color: var(--fail); }}
        section {{
            background: var(--card);
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        section h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .check-list {{ list-style: none; }}
        .check-item {{
            display: flex;
            align-items: flex-start;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .check-item:last-child {{ border-bottom: none; }}
        .status {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 1rem;
            flex-shrink: 0;
            font-size: 0.75rem;
        }}
        .status.pass {{ background: var(--pass); }}
        .status.warn {{ background: var(--warn); }}
        .status.fail {{ background: var(--fail); }}
        .status.info {{ background: var(--info); }}
        .check-content {{ flex: 1; }}
        .check-title {{ font-weight: 500; }}
        .check-detail {{ color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .badge.pass {{ background: rgba(34,197,94,0.2); color: var(--pass); }}
        .badge.warn {{ background: rgba(245,158,11,0.2); color: var(--warn); }}
        .badge.fail {{ background: rgba(239,68,68,0.2); color: var(--fail); }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .metric {{
            background: rgba(255,255,255,0.05);
            padding: 1rem;
            border-radius: 0.5rem;
            text-align: center;
        }}
        .metric .value {{ font-size: 1.5rem; font-weight: bold; }}
        .metric .label {{ color: var(--muted); font-size: 0.875rem; }}
        footer {{
            text-align: center;
            color: var(--muted);
            margin-top: 3rem;
            padding: 1rem;
        }}
        .recommendations {{
            background: rgba(59,130,246,0.1);
            border-left: 4px solid var(--info);
            padding: 1rem;
            margin-top: 1rem;
            border-radius: 0 0.5rem 0.5rem 0;
        }}
        .recommendations h4 {{ color: var(--info); margin-bottom: 0.5rem; }}
        code {{
            background: rgba(255,255,255,0.1);
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
        }}
        @media print {{
            body {{ background: white; color: black; }}
            .container {{ max-width: 100%; }}
            section {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WordPress Health Report</h1>
            <div class="meta">
                <strong>{site}</strong><br>
                Generated: {timestamp}
            </div>
        </header>

        <div class="score-card">
            <div class="score {overall_class}">
                <div class="number">{overall_score}</div>
                <div class="label">Overall Score</div>
            </div>
            <div class="score {security_class}">
                <div class="number">{security_score}</div>
                <div class="label">Security</div>
            </div>
            <div class="score {performance_class}">
                <div class="number">{performance_score}</div>
                <div class="label">Performance</div>
            </div>
        </div>

        {sections}

        <footer>
            <p>Generated by WordPress Health Report Tool</p>
            <p>Part of wp-performance-review skill</p>
        </footer>
    </div>
</body>
</html>
"""


def fetch_url(url: str, timeout: int = 10):
    """Fetch URL and return response data"""
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (WordPress Report Generator)')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return response.read(), dict(response.headers), response.status, None
    except urllib.error.HTTPError as e:
        return None, dict(e.headers) if hasattr(e, 'headers') else {}, e.code, str(e)
    except Exception as e:
        return None, {}, 0, str(e)


def check_ssl(hostname: str) -> dict:
    """Check SSL certificate"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                days_left = (expires - datetime.now()).days
                return {
                    "valid": True,
                    "days_left": days_left,
                    "issuer": dict(x[0] for x in cert.get('issuer', [])).get('organizationName', 'Unknown'),
                    "expires": cert['notAfter']
                }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def check_headers(headers: dict) -> list:
    """Check security headers"""
    results = []
    checks = [
        ("Strict-Transport-Security", "HSTS enforces HTTPS connections"),
        ("X-Frame-Options", "Prevents clickjacking attacks"),
        ("X-Content-Type-Options", "Prevents MIME sniffing"),
        ("Content-Security-Policy", "Controls resource loading"),
        ("X-XSS-Protection", "Legacy XSS protection"),
        ("Referrer-Policy", "Controls referrer information"),
    ]

    headers_lower = {k.lower(): v for k, v in headers.items()}

    for header, desc in checks:
        present = header.lower() in headers_lower
        results.append({
            "name": header,
            "present": present,
            "description": desc,
            "value": headers_lower.get(header.lower(), "")
        })

    return results


def check_exposed_files(base_url: str) -> list:
    """Check for exposed sensitive files"""
    results = []
    files = [
        ("/wp-config.php.bak", "critical", "Config backup with credentials"),
        ("/.git/config", "critical", "Git repository exposed"),
        ("/.env", "critical", "Environment file"),
        ("/debug.log", "warning", "Debug log file"),
        ("/wp-content/debug.log", "warning", "WordPress debug log"),
        ("/xmlrpc.php", "warning", "XML-RPC endpoint"),
        ("/readme.html", "info", "WordPress readme"),
    ]

    for path, severity, desc in files:
        url = base_url.rstrip('/') + path
        _, _, status, _ = fetch_url(url, timeout=5)
        if status == 200:
            results.append({
                "path": path,
                "severity": severity,
                "description": desc
            })

    return results


def measure_performance(url: str) -> dict:
    """Measure response time"""
    import time
    try:
        start = time.time()
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=context) as response:
            first_byte = time.time()
            content = response.read()
            end = time.time()
            return {
                "ttfb": round((first_byte - start) * 1000),
                "total": round((end - start) * 1000),
                "size": len(content),
                "status": response.status
            }
    except Exception as e:
        return {"error": str(e)}


def detect_wordpress(body: bytes) -> dict:
    """Detect WordPress and version"""
    if not body:
        return {"detected": False}

    html = body.decode('utf-8', errors='ignore')
    result = {"detected": False, "version": None}

    if 'wp-content' in html or 'wp-includes' in html:
        result["detected"] = True

    meta_match = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress\s*([\d.]+)?["\']', html, re.I)
    if meta_match:
        result["version"] = meta_match.group(1)

    return result


def generate_section_html(title: str, icon: str, items: list) -> str:
    """Generate HTML for a section"""
    items_html = ""
    for item in items:
        status = item.get("status", "info")
        icon_char = {"pass": "✓", "warn": "!", "fail": "✗", "info": "i"}.get(status, "?")
        items_html += f"""
        <li class="check-item">
            <div class="status {status}">{icon_char}</div>
            <div class="check-content">
                <div class="check-title">{item.get('title', '')}</div>
                <div class="check-detail">{item.get('detail', '')}</div>
            </div>
        </li>
        """

    return f"""
    <section>
        <h2>{icon} {title}</h2>
        <ul class="check-list">
            {items_html}
        </ul>
    </section>
    """


def calculate_scores(results: dict) -> dict:
    """Calculate health scores"""
    security_score = 100
    performance_score = 100

    # Security deductions
    if not results.get("ssl", {}).get("valid"):
        security_score -= 30

    headers = results.get("headers", [])
    missing_headers = len([h for h in headers if not h["present"]])
    security_score -= missing_headers * 5

    exposed = results.get("exposed_files", [])
    for f in exposed:
        if f["severity"] == "critical":
            security_score -= 20
        elif f["severity"] == "warning":
            security_score -= 10

    # Performance deductions
    perf = results.get("performance", {})
    ttfb = perf.get("ttfb", 0)
    if ttfb > 600:
        performance_score -= 30
    elif ttfb > 400:
        performance_score -= 20
    elif ttfb > 200:
        performance_score -= 10

    size = perf.get("size", 0)
    if size > 3000000:  # 3MB
        performance_score -= 20
    elif size > 1500000:  # 1.5MB
        performance_score -= 10

    security_score = max(0, min(100, security_score))
    performance_score = max(0, min(100, performance_score))
    overall = (security_score + performance_score) // 2

    return {
        "security": security_score,
        "performance": performance_score,
        "overall": overall
    }


def score_class(score: int) -> str:
    """Get CSS class for score"""
    if score >= 80:
        return "pass"
    elif score >= 50:
        return "warn"
    return "fail"


def generate_report(url: str, output_path: Optional[str] = None) -> str:
    """Generate full HTML report"""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"Scanning {url}...")

    # Gather data
    results = {}

    print("  Checking SSL...")
    results["ssl"] = check_ssl(hostname)

    print("  Fetching page...")
    body, headers, status, error = fetch_url(url)

    print("  Checking headers...")
    results["headers"] = check_headers(headers)

    print("  Detecting WordPress...")
    results["wordpress"] = detect_wordpress(body)

    print("  Checking exposed files...")
    results["exposed_files"] = check_exposed_files(base_url)

    print("  Measuring performance...")
    results["performance"] = measure_performance(url)

    # Calculate scores
    scores = calculate_scores(results)

    # Build sections
    sections = ""

    # SSL Section
    ssl_items = []
    ssl_data = results["ssl"]
    if ssl_data.get("valid"):
        ssl_items.append({
            "status": "pass" if ssl_data["days_left"] > 30 else "warn",
            "title": f"SSL Certificate Valid ({ssl_data['days_left']} days remaining)",
            "detail": f"Issuer: {ssl_data.get('issuer', 'Unknown')} | Expires: {ssl_data.get('expires', 'Unknown')}"
        })
    else:
        ssl_items.append({
            "status": "fail",
            "title": "SSL Certificate Invalid or Missing",
            "detail": ssl_data.get("error", "Could not validate certificate")
        })
    sections += generate_section_html("SSL Certificate", "🔒", ssl_items)

    # Security Headers Section
    header_items = []
    for h in results["headers"]:
        header_items.append({
            "status": "pass" if h["present"] else "warn",
            "title": h["name"],
            "detail": h["value"][:100] if h["present"] else f"Missing - {h['description']}"
        })
    sections += generate_section_html("Security Headers", "🛡️", header_items)

    # Exposed Files Section
    exposed_items = []
    if results["exposed_files"]:
        for f in results["exposed_files"]:
            status_map = {"critical": "fail", "warning": "warn", "info": "info"}
            exposed_items.append({
                "status": status_map.get(f["severity"], "info"),
                "title": f["path"],
                "detail": f["description"]
            })
    else:
        exposed_items.append({
            "status": "pass",
            "title": "No exposed sensitive files detected",
            "detail": "Common sensitive files are properly protected"
        })
    sections += generate_section_html("Exposed Files", "📁", exposed_items)

    # Performance Section
    perf = results["performance"]
    perf_items = []
    if "error" not in perf:
        ttfb = perf["ttfb"]
        ttfb_status = "pass" if ttfb < 200 else "warn" if ttfb < 600 else "fail"
        perf_items.append({
            "status": ttfb_status,
            "title": f"Time to First Byte: {ttfb}ms",
            "detail": "Target: < 200ms for optimal performance"
        })

        size_kb = perf["size"] / 1024
        size_status = "pass" if size_kb < 1500 else "warn" if size_kb < 3000 else "fail"
        perf_items.append({
            "status": size_status,
            "title": f"Page Size: {size_kb:.0f} KB",
            "detail": "Target: < 1.5MB for fast loading"
        })

        perf_items.append({
            "status": "info",
            "title": f"Total Load Time: {perf['total']}ms",
            "detail": "Full page download time"
        })
    else:
        perf_items.append({
            "status": "fail",
            "title": "Could not measure performance",
            "detail": perf["error"]
        })
    sections += generate_section_html("Performance", "⚡", perf_items)

    # WordPress Section
    wp = results["wordpress"]
    wp_items = []
    if wp["detected"]:
        wp_items.append({
            "status": "info",
            "title": f"WordPress Detected (v{wp.get('version', 'Unknown')})",
            "detail": "Consider hiding version information for security"
        })
    else:
        wp_items.append({
            "status": "pass",
            "title": "WordPress version not exposed",
            "detail": "Version information is hidden or site is not WordPress"
        })
    sections += generate_section_html("WordPress Detection", "📝", wp_items)

    # Generate final HTML
    html = HTML_TEMPLATE.format(
        site=hostname,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        overall_score=scores["overall"],
        overall_class=score_class(scores["overall"]),
        security_score=scores["security"],
        security_class=score_class(scores["security"]),
        performance_score=scores["performance"],
        performance_class=score_class(scores["performance"]),
        sections=sections
    )

    # Save or print
    if output_path:
        output_file = Path(output_path)
        output_file.write_text(html)
        print(f"\n✅ Report saved to: {output_file.absolute()}")
        return str(output_file.absolute())
    else:
        # Auto-generate filename
        filename = f"wp-report-{hostname.replace('.', '-')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        Path(filename).write_text(html)
        print(f"\n✅ Report saved to: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description='WordPress Health Report Generator')
    parser.add_argument('url', help='WordPress site URL')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('--json', action='store_true', help='Output raw data as JSON')
    args = parser.parse_args()

    url = args.url
    if not url.startswith('http'):
        url = 'https://' + url

    if args.json:
        # Just output raw scan data
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.netloc
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        results = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "ssl": check_ssl(hostname),
            "performance": measure_performance(url),
        }
        body, headers, _, _ = fetch_url(url)
        results["headers"] = check_headers(headers)
        results["wordpress"] = detect_wordpress(body)
        results["exposed_files"] = check_exposed_files(base_url)
        results["scores"] = calculate_scores(results)

        print(json.dumps(results, indent=2, default=str))
    else:
        generate_report(url, args.output)


if __name__ == "__main__":
    main()
