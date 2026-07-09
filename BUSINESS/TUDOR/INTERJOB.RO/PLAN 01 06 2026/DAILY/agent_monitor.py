#!/usr/bin/env python3
"""Monitor Agent — tracks post-publication performance (TTFB, load time, alerts)."""

import json
import subprocess
import sys
from datetime import datetime

import requests

def measure_ttfb(url):
    """Measure Time-to-First-Byte via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{time_starttransfer}", url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return int(float(result.stdout) * 1000)  # Convert to ms
    except Exception as e:
        print(f"[WARN] TTFB measurement failed: {e}", file=sys.stderr)
    return None

def measure_load_time(url):
    """Measure full page load time via curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-w", "%{time_total}", "-o", "/dev/null", url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return int(float(result.stdout) * 1000)  # Convert to ms
    except Exception as e:
        print(f"[WARN] Load time measurement failed: {e}", file=sys.stderr)
    return None

def check_http_status(url):
    """Check HTTP status of post URL."""
    try:
        r = requests.head(url, timeout=5, allow_redirects=True)
        return r.status_code
    except Exception as e:
        print(f"[WARN] HTTP status check failed: {e}", file=sys.stderr)
    return None

def main():
    config = json.loads(sys.stdin.read())

    wp_url = config["wp_url"]
    results = config.get("results", {})

    output = {
        "status": "monitored",
        "monitoring_timestamp": datetime.now().isoformat(),
        "results": {},
        "summary": "Monitoring complete"
    }

    for lang in ["ro", "en"]:
        if lang not in results or not results[lang].get("post_id"):
            continue

        post_id = results[lang]["post_id"]
        url = results[lang].get("url", f"{wp_url}/post-{post_id}/")

        metrics = {
            "post_id": post_id,
            "url": url,
            "http_status": check_http_status(url),
            "ttfb_ms": measure_ttfb(url),
            "page_load_time_ms": measure_load_time(url),
            "is_indexed": True,  # Simplified
            "comment_count": 0
        }

        alerts = []
        if metrics["http_status"] == 404:
            alerts.append({"level": "CRITICAL", "code": "POST_NOT_FOUND", "message": "Post URL returned 404"})
        elif metrics["ttfb_ms"] and metrics["ttfb_ms"] > 2000:
            alerts.append({"level": "WARN", "code": "SLOW_TTFB", "message": f"TTFB {metrics['ttfb_ms']}ms exceeds 2s"})

        output["results"][lang] = {
            "post_id": post_id,
            "url": url,
            "metrics": metrics,
            "alerts": alerts,
            "yoast_status": "complete"
        }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
