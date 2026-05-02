#!/usr/bin/env python3
"""
Campaign Monitor with Local LLM
Monitors A2 SMTP campaigns, uses local LLM for analysis, alerts on issues.

Usage:
    campaign_monitor_llm.py                    # Monitor all active campaigns
    campaign_monitor_llm.py --campaign NAME    # Monitor specific campaign
    campaign_monitor_llm.py --status           # Show status only
    campaign_monitor_llm.py --check            # Single health check
    campaign_monitor_llm.py --watch            # Continuous monitoring

Requires: LM Studio running at localhost:1234
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import time
import subprocess
import argparse
import smtplib
import ssl
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from alerting import send_telegram
from skills_common import get_a2_password

# Configuration
LLM_URL = "http://localhost:1234/v1/chat/completions"
LLM_MODEL = "llama-3.2-3b-instruct"  # Smallest, fastest - good for simple monitoring
CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS")
SKILLS_DIR = Path("/opt/ACTIVE/INFRA/SKILLS")

# Campaign definitions
CAMPAIGNS = {
    "LUCIAN_HORECA": {
        "dir": "LUCIAN_HORECA_2026",
        "script": "send_lucian_horeca.py",
        "tmux_session": "lucian_horeca",
        "senders": [
            {"domain": "horecaworkers.eu", "email": "office@horecaworkers.eu"},
            {"domain": "horecaworkers2026.eu", "email": "office@horecaworkers2026.eu"},
            {"domain": "horecaworkers2026.com", "email": "office@horecaworkers2026.com"},
            {"domain": "horecaworkers2026.online", "email": "office@horecaworkers2026.online"},
        ],
        "daily_limit": 2000,
        "type": "a2",
    },
}


def log(msg: str, level: str = "INFO"):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def query_llm(prompt: str, system: str = "You are a system monitoring assistant. Be concise.") -> Optional[str]:
    """Query local LLM for analysis."""
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"LLM query failed: {e}", "WARN")
    return None


def check_tmux_session(session_name: str) -> Tuple[bool, str]:
    """Check if tmux session exists and get recent output."""
    try:
        # Check if session exists
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, "Session not running"

        # Get recent output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session_name, "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def check_a2_smtp(domain: str, email: str) -> Tuple[bool, str]:
    """Test A2 SMTP connection."""
    password = get_a2_password(domain)
    if not password:
        return False, "No password found"

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(f"mail.{domain}", 465, context=ctx, timeout=10) as server:
            server.login(email, password)
        return True, "OK"
    except Exception as e:
        return False, str(e)[:50]


def get_campaign_stats(campaign_dir: Path) -> Dict:
    """Get campaign statistics from state and logs."""
    stats = {
        "sent_today": 0,
        "sent_total": 0,
        "remaining": 0,
        "errors_today": 0,
        "last_send": None,
        "bounce_rate": 0,
    }

    # Read state file
    state_file = campaign_dir / ".state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
            stats["sent_total"] = len(state.get("sent", {}))

            # Count today's sends
            today = date.today().isoformat()
            for email, info in state.get("sent", {}).items():
                if info.get("date", "")[:10] == today:
                    stats["sent_today"] += 1
                    if stats["last_send"] is None or info.get("date", "") > stats["last_send"]:
                        stats["last_send"] = info.get("date")
        except:
            pass

    # Read contacts
    contacts_file = campaign_dir / "contacts" / "contacts.csv"
    if contacts_file.exists():
        try:
            with open(contacts_file) as f:
                total = sum(1 for _ in f) - 1  # minus header
            stats["remaining"] = total - stats["sent_total"]
        except:
            pass

    # Read today's log for errors
    log_file = campaign_dir / "logs" / f"send_{date.today().isoformat()}.log"
    if log_file.exists():
        try:
            content = log_file.read_text()
            stats["errors_today"] = content.lower().count("error") + content.lower().count("fail")

            # Calculate bounce rate
            total_lines = content.count("\n")
            if total_lines > 0:
                bounces = content.lower().count("bounce") + content.lower().count("550")
                stats["bounce_rate"] = (bounces / total_lines) * 100
        except:
            pass

    return stats


def analyze_with_llm(campaign: str, stats: Dict, log_excerpt: str) -> Optional[str]:
    """Use LLM to analyze campaign health."""
    prompt = f"""Analyze this email campaign status and identify any issues:

Campaign: {campaign}
Sent today: {stats['sent_today']}
Total sent: {stats['sent_total']}
Remaining: {stats['remaining']}
Errors today: {stats['errors_today']}
Bounce rate: {stats['bounce_rate']:.1f}%
Last send: {stats['last_send']}

Recent log excerpt:
{log_excerpt[-1000:] if log_excerpt else 'No recent logs'}

Respond with:
1. STATUS: OK/WARNING/CRITICAL
2. ISSUES: List any problems (or "None")
3. ACTION: Recommended action (or "Continue")
"""
    return query_llm(prompt)


def monitor_campaign(name: str, config: Dict, verbose: bool = True) -> Dict:
    """Monitor a single campaign."""
    campaign_dir = CAMPAIGNS_DIR / config["dir"]
    result = {
        "name": name,
        "status": "unknown",
        "issues": [],
        "stats": {},
    }

    # Check tmux session
    session_running, session_output = check_tmux_session(config.get("tmux_session", ""))
    if config.get("tmux_session"):
        if not session_running:
            result["issues"].append("Tmux session not running")
            result["status"] = "critical"
        elif verbose:
            log(f"Session '{config['tmux_session']}' is running")

    # Check SMTP connections (for A2 campaigns)
    if config.get("type") == "a2":
        smtp_ok = 0
        smtp_fail = []
        for sender in config.get("senders", []):
            ok, msg = check_a2_smtp(sender["domain"], sender["email"])
            if ok:
                smtp_ok += 1
            else:
                smtp_fail.append(f"{sender['domain']}: {msg}")

        if smtp_fail:
            result["issues"].extend(smtp_fail)
            if smtp_ok == 0:
                result["status"] = "critical"
            else:
                result["status"] = "warning"
        elif verbose:
            log(f"All {smtp_ok} SMTP connections OK")

    # Get stats
    stats = get_campaign_stats(campaign_dir)
    result["stats"] = stats

    if verbose:
        log(f"Stats: sent_today={stats['sent_today']}, remaining={stats['remaining']}, errors={stats['errors_today']}")

    # Check for issues
    if stats["errors_today"] > 10:
        result["issues"].append(f"High error count: {stats['errors_today']}")
        result["status"] = "warning"

    if stats["bounce_rate"] > 5:
        result["issues"].append(f"High bounce rate: {stats['bounce_rate']:.1f}%")
        result["status"] = "critical"

    # LLM analysis
    if result["issues"] or stats["errors_today"] > 0:
        log("Requesting LLM analysis...")
        analysis = analyze_with_llm(name, stats, session_output)
        if analysis:
            result["llm_analysis"] = analysis
            log(f"LLM: {analysis[:200]}...")

    # Set final status
    if not result["issues"] and result["status"] == "unknown":
        result["status"] = "ok"

    return result


def send_alert(campaign: str, issues: List[str], stats: Dict):
    """Send Telegram alert for issues."""
    msg = f"⚠️ Campaign Monitor Alert: {campaign}\n\n"
    msg += f"Issues:\n" + "\n".join(f"- {i}" for i in issues)
    msg += f"\n\nStats: {stats['sent_today']} sent today, {stats['remaining']} remaining"

    try:
        send_telegram(msg)
        log("Alert sent to Telegram")
    except Exception as e:
        log(f"Failed to send alert: {e}", "ERROR")


def show_status():
    """Show status of all campaigns."""
    print("=" * 60)
    print("CAMPAIGN MONITOR STATUS")
    print("=" * 60)

    # Check Dashboard
    dash = check_dashboard()
    if dash["running"]:
        endpoints_ok = sum(1 for v in dash["endpoints"].values() if v == "ok")
        total_endpoints = len(dash["endpoints"])
        print(f"Dashboard: Running ({dash['campaigns_count']} campaigns, {endpoints_ok}/{total_endpoints} endpoints OK)")
        if dash["issues"]:
            for issue in dash["issues"]:
                print(f"  ⚠ {issue}")
    else:
        print("Dashboard: NOT RUNNING")

    # Check LLM availability
    try:
        r = requests.get("http://localhost:1234/v1/models", timeout=5)
        if r.status_code == 200:
            models = [m["id"] for m in r.json().get("data", [])]
            print(f"LLM: Available ({len(models)} models)")
        else:
            print("LLM: Not responding")
    except:
        print("LLM: Not available")

    print()

    for name, config in CAMPAIGNS.items():
        result = monitor_campaign(name, config, verbose=False)

        status_icon = {"ok": "✓", "warning": "⚠", "critical": "✗"}.get(result["status"], "?")
        print(f"{status_icon} {name}")
        print(f"  Sent today: {result['stats'].get('sent_today', 0)}")
        print(f"  Remaining: {result['stats'].get('remaining', 0)}")

        if result["issues"]:
            for issue in result["issues"]:
                print(f"  ⚠ {issue}")
        print()


def watch_campaigns(interval: int = 300):
    """Continuous monitoring loop."""
    log("Starting continuous monitoring (Ctrl+C to stop)")
    log(f"Check interval: {interval} seconds")

    while True:
        try:
            for name, config in CAMPAIGNS.items():
                log(f"Checking {name}...")
                result = monitor_campaign(name, config)

                if result["status"] in ("warning", "critical") and result["issues"]:
                    send_alert(name, result["issues"], result["stats"])

            log(f"Next check in {interval} seconds...")
            time.sleep(interval)

        except KeyboardInterrupt:
            log("Monitoring stopped")
            break
        except Exception as e:
            log(f"Error in monitoring loop: {e}", "ERROR")
            time.sleep(60)


def check_dashboard() -> dict:
    """Check dashboard health and all API endpoints."""
    DASHBOARD_URL = "http://localhost:8088"
    ENDPOINTS = {
        "campaigns": "/api/campaigns",
        "senders": "/api/senders",
        "reports": "/api/reports",
        "a2_warmup": "/api/a2-warmup",
        "health": "/api/health",
        "governor": "/api/governor",
    }

    result = {
        "status": "ok",
        "running": False,
        "endpoints": {},
        "issues": [],
        "campaigns_count": 0,
        "running_campaigns": 0,
    }

    # Check if dashboard is running
    try:
        resp = requests.get(f"{DASHBOARD_URL}/api/campaigns", timeout=5)
        result["running"] = True

        if resp.status_code == 200:
            campaigns = resp.json()
            result["campaigns_count"] = len(campaigns)
            result["running_campaigns"] = sum(1 for c in campaigns if c.get("is_running"))
            result["endpoints"]["campaigns"] = "ok"
        else:
            result["endpoints"]["campaigns"] = f"HTTP {resp.status_code}"
            result["issues"].append(f"Campaigns API returned {resp.status_code}")
    except Exception as e:
        result["running"] = False
        result["status"] = "critical"
        result["issues"].append(f"Dashboard not responding: {e}")
        return result

    # Check other endpoints
    for name, path in ENDPOINTS.items():
        if name == "campaigns":
            continue
        try:
            resp = requests.get(f"{DASHBOARD_URL}{path}", timeout=10)
            if resp.status_code == 200:
                result["endpoints"][name] = "ok"
            else:
                result["endpoints"][name] = f"HTTP {resp.status_code}"
                result["issues"].append(f"{name} API returned {resp.status_code}")
        except Exception as e:
            result["endpoints"][name] = f"error: {str(e)[:30]}"
            result["issues"].append(f"{name} API failed: {e}")

    # Determine overall status
    if result["issues"]:
        result["status"] = "warning" if result["running"] else "critical"

    return result


def single_check(include_dashboard: bool = True):
    """Single health check of all campaigns."""
    all_ok = True

    # Check dashboard first
    if include_dashboard:
        dash_result = check_dashboard()
        if dash_result["status"] != "ok":
            all_ok = False
            if dash_result["issues"]:
                send_telegram(f"Dashboard Issues:\n" + "\n".join(dash_result["issues"]))
            log(f"Dashboard: {dash_result['status']}", "WARN" if dash_result["status"] == "warning" else "ERROR")
        else:
            log(f"Dashboard: OK ({dash_result['campaigns_count']} campaigns)")

    for name, config in CAMPAIGNS.items():
        result = monitor_campaign(name, config)

        if result["status"] != "ok":
            all_ok = False
            if result["issues"]:
                send_alert(name, result["issues"], result["stats"])

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Campaign Monitor with Local LLM")
    parser.add_argument("--campaign", "-c", help="Monitor specific campaign")
    parser.add_argument("--status", "-s", action="store_true", help="Show status only")
    parser.add_argument("--check", action="store_true", help="Single health check")
    parser.add_argument("--watch", "-w", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", "-i", type=int, default=300, help="Watch interval (seconds)")
    parser.add_argument("--dashboard", "-d", action="store_true", help="Check dashboard only")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip dashboard checks")
    args = parser.parse_args()

    if args.dashboard:
        # Dashboard check only
        result = check_dashboard()
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result["status"] == "ok" else 1)
    elif args.status:
        show_status()
    elif args.check:
        ok = single_check(include_dashboard=not args.no_dashboard)
        sys.exit(0 if ok else 1)
    elif args.watch:
        watch_campaigns(args.interval)
    elif args.campaign:
        if args.campaign in CAMPAIGNS:
            result = monitor_campaign(args.campaign, CAMPAIGNS[args.campaign])
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Unknown campaign: {args.campaign}")
            print(f"Available: {', '.join(CAMPAIGNS.keys())}")
            sys.exit(1)
    else:
        show_status()


if __name__ == "__main__":
    main()
