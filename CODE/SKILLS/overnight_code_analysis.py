#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Overnight Code Analysis - Comprehensive code review for both machines.
Runs overnight, generates report with proposals, sends at 9 AM.

Usage:
    python3 overnight_code_analysis.py --analyze   # Run analysis (3 AM cron)
    python3 overnight_code_analysis.py --send      # Send report (9 AM cron)
"""
import os
import sys
import json
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any

# Load environment variables FIRST
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
except ImportError:
    pass

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

# Configuration
REPORT_DIR = "/tmp/code_analysis"
REPORT_FILE = f"{REPORT_DIR}/report_{date.today().isoformat()}.json"
FINAL_REPORT = f"{REPORT_DIR}/report_{date.today().isoformat()}.txt"

RASPIBIG_PATHS = [
    "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE",
    "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED",
    "/opt/ACTIVE/INFRA/SKILLS",
]

RASPI_PATHS = [
    "/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS",
    "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED",
]

TELEGRAM_BOT = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
EMAIL_TO = "office@interjob.ro"

def run_code_reviewer(path: str, host: str = "local") -> Dict:
    """Run code_reviewer.py on a path."""
    try:
        if host == "local":
            cmd = ["/opt/ACTIVE/INFRA/venv/bin/python3", "/opt/ACTIVE/INFRA/SKILLS/code_reviewer.py", path, "--json"]
        else:
            cmd = ["ssh", host, f"/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/code_reviewer.py {path} --json 2>/dev/null"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # code_reviewer exits with 1 if critical/high issues found, but still outputs JSON
        if result.stdout.strip():
            try:
                return json.loads(result.stdout)
            except Exception:
                pass

        return {"path": path, "issues": [], "error": result.stderr[:200] if result.stderr else None}
    except Exception as e:
        return {"path": path, "issues": [], "error": str(e)}

def count_files(path: str, host: str = "local") -> int:
    """Count Python files in path."""
    try:
        if host == "local":
            return len(list(Path(path).rglob("*.py")))
        else:
            result = subprocess.run(
                ["ssh", host, f"find {path} -name '*.py' 2>/dev/null | wc -l"],
                capture_output=True, text=True, timeout=30
            )
            return int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    except Exception:
        return 0

def analyze_machine(name: str, paths: List[str], host: str = "local") -> Dict:
    """Analyze all paths on a machine."""
    print(f"\n{'='*60}")
    print(f"Analyzing {name}...")
    print(f"{'='*60}")

    results = {
        "machine": name,
        "host": host,
        "timestamp": datetime.now().isoformat(),
        "paths": [],
        "summary": {
            "total_files": 0,
            "total_issues": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_category": {}
        }
    }

    for path in paths:
        print(f"  Reviewing {path}...")

        file_count = count_files(path, host)
        review = run_code_reviewer(path, host)

        issues = review.get("issues", [])

        path_result = {
            "path": path,
            "files": file_count,
            "issues": len(issues),
            "details": issues[:200]  # Limit to top 200 issues per path
        }

        results["paths"].append(path_result)
        results["summary"]["total_files"] += file_count
        results["summary"]["total_issues"] += len(issues)

        for issue in issues:
            sev = issue.get("severity", "low")
            cat = issue.get("category", "other")
            results["summary"]["by_severity"][sev] = results["summary"]["by_severity"].get(sev, 0) + 1
            results["summary"]["by_category"][cat] = results["summary"]["by_category"].get(cat, 0) + 1

        print(f"    {file_count} files, {len(issues)} issues")

    return results

def generate_proposals(results: List[Dict]) -> List[Dict]:
    """Generate improvement proposals based on analysis."""
    proposals = []

    for machine in results:
        name = machine["machine"]
        summary = machine["summary"]

        # Critical issues
        if summary["by_severity"].get("critical", 0) > 0:
            proposals.append({
                "priority": "CRITICAL",
                "machine": name,
                "proposal": f"Fix {summary['by_severity']['critical']} critical issues immediately",
                "category": "security"
            })

        # High issues
        if summary["by_severity"].get("high", 0) > 5:
            proposals.append({
                "priority": "HIGH",
                "machine": name,
                "proposal": f"Address {summary['by_severity']['high']} high-severity issues this week",
                "category": "quality"
            })

        # Category-specific proposals
        for cat, count in summary["by_category"].items():
            if count >= 10:
                if cat == "error_handling":
                    proposals.append({
                        "priority": "MEDIUM",
                        "machine": name,
                        "proposal": f"Improve error handling in {count} locations",
                        "category": cat
                    })
                elif cat == "security":
                    proposals.append({
                        "priority": "HIGH",
                        "machine": name,
                        "proposal": f"Review {count} potential security issues",
                        "category": cat
                    })
                elif cat == "unused_code":
                    proposals.append({
                        "priority": "LOW",
                        "machine": name,
                        "proposal": f"Clean up {count} unused imports/variables",
                        "category": cat
                    })

        # Check for path-specific issues
        for path_result in machine["paths"]:
            if path_result["issues"] > 20:
                proposals.append({
                    "priority": "MEDIUM",
                    "machine": name,
                    "proposal": f"Refactor {path_result['path']} ({path_result['issues']} issues)",
                    "category": "refactoring"
                })

    # Sort by priority
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    proposals.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return proposals

def format_report(results: List[Dict], proposals: List[Dict]) -> str:
    """Format results as readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"CODE ANALYSIS REPORT - {date.today().isoformat()}")
    lines.append("=" * 60)
    lines.append("")

    # Summary
    total_files = sum(r["summary"]["total_files"] for r in results)
    total_issues = sum(r["summary"]["total_issues"] for r in results)

    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total files analyzed: {total_files}")
    lines.append(f"Total issues found: {total_issues}")
    lines.append("")

    # Per machine
    for machine in results:
        name = machine["machine"]
        summary = machine["summary"]

        lines.append(f"{name.upper()}")
        lines.append(f"  Files: {summary['total_files']}")
        lines.append(f"  Issues: {summary['total_issues']}")

        if summary["by_severity"]:
            sev_str = ", ".join(f"{k}: {v}" for k, v in summary["by_severity"].items() if v > 0)
            lines.append(f"  By severity: {sev_str}")

        lines.append("")

        # Top issues per path
        for path_result in machine["paths"]:
            if path_result["issues"] > 0:
                lines.append(f"  {path_result['path']}")
                lines.append(f"    {path_result['files']} files, {path_result['issues']} issues")

                # Show top 5 issues with file:line links
                for issue in path_result["details"][:5]:
                    file_path = issue.get('file', '')
                    line_num = issue.get('line', 0)
                    severity = issue.get('severity', '?')
                    message = issue.get('message', '')[:80]

                    if file_path and line_num:
                        lines.append(f"    - [{severity}] {file_path}:{line_num}")
                        lines.append(f"      {message}")
                    else:
                        lines.append(f"    - [{severity}] {message}")

        lines.append("")

    # Critical and High Issues with full paths
    lines.append("=" * 60)
    lines.append("CRITICAL & HIGH SEVERITY ISSUES")
    lines.append("=" * 60)
    lines.append("")

    critical_high = []
    for machine in results:
        for path_result in machine["paths"]:
            for issue in path_result.get("details", []):
                if issue.get("severity") in ["critical", "high"]:
                    critical_high.append({
                        "machine": machine["machine"],
                        **issue
                    })

    if critical_high:
        # Group by severity
        for severity in ["critical", "high"]:
            issues_of_sev = [i for i in critical_high if i.get("severity") == severity]
            if issues_of_sev:
                lines.append(f"{severity.upper()} ({len(issues_of_sev)}):")
                for issue in issues_of_sev[:20]:  # Limit to 20 per severity
                    file_path = issue.get('file', 'unknown')
                    line_num = issue.get('line', 0)
                    msg = issue.get('message', '')[:100]
                    lines.append(f"  {file_path}:{line_num}")
                    lines.append(f"    {msg}")
                if len(issues_of_sev) > 20:
                    lines.append(f"  ... and {len(issues_of_sev) - 20} more")
                lines.append("")
    else:
        lines.append("No critical or high severity issues found!")
        lines.append("")

    # Proposals
    lines.append("=" * 60)
    lines.append("PROPOSALS")
    lines.append("=" * 60)
    lines.append("")

    if not proposals:
        lines.append("No significant issues requiring proposals.")
    else:
        for i, p in enumerate(proposals, 1):
            lines.append(f"{i}. [{p['priority']}] {p['machine']}: {p['proposal']}")

    lines.append("")
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    return "\n".join(lines)

def send_telegram(message: str):
    """Send message to Telegram."""
    import requests

    if not TELEGRAM_BOT or not TELEGRAM_CHAT:
        print("Telegram not configured")
        return False

    try:
        # Truncate if too long
        if len(message) > 4000:
            message = message[:3900] + "\n\n... (truncated)"

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
        resp = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=30)

        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def send_email(subject: str, body: str, to: str):
    """Send email via Brevo."""
    import requests

    api_key = os.getenv("BREVO_API_KEY", "")
    if not api_key:
        print("Brevo API key not configured")
        return False

    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        data = {
            "sender": {"name": "Code Analysis", "email": "noreply@interjob.ro"},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body
        }

        resp = requests.post(url, headers=headers, json=data, timeout=30)
        return resp.status_code in [200, 201]
    except Exception as e:
        print(f"Email error: {e}")
        return False

def run_analysis():
    """Run full analysis on both machines."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    print(f"Starting overnight code analysis - {datetime.now()}")

    results = []

    # Analyze raspibig (local)
    results.append(analyze_machine("raspibig", RASPIBIG_PATHS, "local"))

    # Analyze raspi (remote)
    results.append(analyze_machine("raspi", RASPI_PATHS, "raspi"))

    # Generate proposals
    proposals = generate_proposals(results)

    # Save JSON results
    with open(REPORT_FILE, "w") as f:
        json.dump({
            "results": results,
            "proposals": proposals,
            "generated": datetime.now().isoformat()
        }, f, indent=2)

    # Save text report
    report = format_report(results, proposals)
    with open(FINAL_REPORT, "w") as f:
        f.write(report)

    print(f"\nAnalysis complete. Report saved to {FINAL_REPORT}")
    print(f"Found {len(proposals)} proposals")

    # Sync report to raspi for sending
    try:
        subprocess.run(["ssh", "raspi", f"mkdir -p {REPORT_DIR}"], timeout=30)
        subprocess.run(["scp", REPORT_FILE, f"raspi:{REPORT_FILE}"], timeout=60)
        subprocess.run(["scp", FINAL_REPORT, f"raspi:{FINAL_REPORT}"], timeout=60)
        print(f"Report synced to raspi")
    except Exception as e:
        print(f"Warning: Could not sync to raspi: {e}")

    return report

def send_report():
    """Send the generated report."""
    if not os.path.exists(FINAL_REPORT):
        print(f"Report not found: {FINAL_REPORT}")
        # Try to generate it
        run_analysis()

    with open(FINAL_REPORT) as f:
        report = f.read()

    # Load proposals count
    proposals_count = 0
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            data = json.load(f)
            proposals_count = len(data.get("proposals", []))

    subject = f"Code Analysis Report - {date.today().isoformat()} ({proposals_count} proposals)"

    # Send email
    print(f"Sending email to {EMAIL_TO}...")
    if send_email(subject, report, EMAIL_TO):
        print("Email sent successfully")
    else:
        print("Email failed")

    # Send Telegram (summary only)
    telegram_msg = f"<b>Code Analysis Report</b>\n"
    telegram_msg += f"<code>{date.today().isoformat()}</code>\n\n"

    # Extract summary
    for line in report.split("\n"):
        if "Total files" in line or "Total issues" in line:
            telegram_msg += f"{line}\n"
        if line.startswith("1. [") or line.startswith("2. [") or line.startswith("3. ["):
            telegram_msg += f"{line}\n"

    telegram_msg += f"\nFull report sent to {EMAIL_TO}"

    print("Sending Telegram...")
    if send_telegram(telegram_msg):
        print("Telegram sent successfully")
    else:
        print("Telegram failed")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Overnight Code Analysis")
    parser.add_argument("--analyze", action="store_true", help="Run analysis")
    parser.add_argument("--send", action="store_true", help="Send report")
    parser.add_argument("--both", action="store_true", help="Analyze and send")
    args = parser.parse_args()

    if args.analyze or args.both:
        run_analysis()

    if args.send or args.both:
        send_report()

    if not (args.analyze or args.send or args.both):
        parser.print_help()

if __name__ == "__main__":
    main()
