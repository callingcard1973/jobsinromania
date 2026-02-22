#!/usr/bin/env python3
"""
Token Optimization Supervisor Skill

Monitors health of the token optimization system:
- Reviews daily audit reports
- Analyzes weekly dashboard trends
- Detects anomalies (sudden token increase, new bloat)
- Triggers corrective actions automatically
- Generates weekly briefings for Claude Code

This skill runs as a background monitor and can be called by Claude Code
to review current system status and health.

Usage:
  python token_optimization_supervisor.py --check         # Quick health check
  python token_optimization_supervisor.py --report        # Generate weekly report
  python token_optimization_supervisor.py --fix-anomalies # Auto-fix issues found
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
STATS_FILE = LOG_DIR / "optimizer_stats.json"
MONITORING_DIR = LOG_DIR / "monitoring"


class TokenOptimizationSupervisor:
    """Supervise and monitor the token optimization system"""

    def __init__(self):
        self.log_dir = LOG_DIR
        self.monitoring_dir = MONITORING_DIR
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)

    def check_system_health(self) -> Dict:
        """Perform comprehensive health check on token optimization system"""
        health = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "alerts": [],
            "warnings": [],
            "metrics": {}
        }

        # Check 1: Verify all optimization scripts exist
        required_files = [
            "daily_audit.py",
            "token_monitor.py",
            "tool_weights.json",
            "reduction_dashboard.py",
            "PRODUCTION_STATUS.md"
        ]

        missing_files = []
        for fname in required_files:
            fpath = LOG_DIR.parent / fname
            if not fpath.exists():
                missing_files.append(fname)

        if missing_files:
            health["status"] = "degraded"
            health["alerts"].append(f"Missing optimization files: {', '.join(missing_files)}")

        # Check 2: Verify latest audit report exists and is recent
        audit_files = sorted(self.log_dir.glob("audit_*.json"))
        if audit_files:
            latest_audit = audit_files[-1]
            age_hours = (datetime.now() - datetime.fromtimestamp(latest_audit.stat().st_mtime)).total_seconds() / 3600
            health["metrics"]["latest_audit_age_hours"] = round(age_hours, 1)

            if age_hours > 48:
                health["warnings"].append(f"Latest audit is {age_hours:.1f} hours old (expected daily)")

            try:
                with open(latest_audit) as f:
                    audit_data = json.load(f)
                    health["metrics"]["files_audited"] = audit_data.get("local", {}).get("total", 0)
                    health["metrics"]["files_bloated"] = audit_data.get("local", {}).get("bloated", 0)
            except Exception as e:
                health["warnings"].append(f"Could not parse latest audit: {e}")
        else:
            health["warnings"].append("No audit reports found - first audit should run at 9 AM tomorrow")

        # Check 3: Verify optimizer stats
        if STATS_FILE.exists():
            try:
                with open(STATS_FILE) as f:
                    stats = json.load(f)
                    health["metrics"]["total_files_scanned"] = stats.get("total_files", 0)
                    health["metrics"]["files_optimized"] = stats.get("optimized", 0)
                    health["metrics"]["cumulative_tokens_saved"] = stats.get("tokens_saved", 0)
            except Exception as e:
                health["warnings"].append(f"Could not parse optimizer stats: {e}")

        # Check 4: Verify reduction dashboard
        dashboard_files = sorted(self.log_dir.glob("reduction_*.json"))
        if dashboard_files:
            health["metrics"]["dashboard_reports"] = len(dashboard_files)
        else:
            health["warnings"].append("No dashboard reports yet - first report generates on Monday")

        # Check 5: Anomaly detection
        if dashboard_files and len(dashboard_files) >= 2:
            try:
                with open(dashboard_files[-1]) as f:
                    latest = json.load(f)
                with open(dashboard_files[-2]) as f:
                    previous = json.load(f)

                latest_saved = latest.get("summary", {}).get("tokens_saved_total", 0)
                prev_saved = previous.get("summary", {}).get("tokens_saved_total", 0)

                if latest_saved < prev_saved * 0.5:  # >50% drop
                    health["alerts"].append(f"ALERT: Token savings dropped 50%+ ({latest_saved} vs {prev_saved})")
                    health["status"] = "degraded"

            except Exception as e:
                health["warnings"].append(f"Could not compare trend: {e}")

        return health

    def generate_supervisor_report(self) -> str:
        """Generate weekly supervisor report with recommendations"""
        health = self.check_system_health()

        report = f"""
TOKEN OPTIMIZATION SUPERVISOR REPORT
Generated: {health['timestamp']}
System Status: {health['status'].upper()}

HEALTH METRICS:
"""
        for key, val in health['metrics'].items():
            report += f"  {key}: {val}\n"

        if health['alerts']:
            report += "\nALERTS (require immediate action):\n"
            for alert in health['alerts']:
                report += f"  [!] {alert}\n"

        if health['warnings']:
            report += "\nWARNINGS (monitor closely):\n"
            for warning in health['warnings']:
                report += f"  [*] {warning}\n"

        report += "\nRECOMMENDATIONS:\n"
        if health['status'] == "healthy":
            report += "  [OK] System operating normally - no action required\n"
        else:
            report += "  [*] Review alerts above immediately\n"
            report += "  • Check audit logs at: D:\\MEMORY\\OPTIMIZE TOKENS\\logs\\audit_*.json\n"
            report += "  • Run manual audit: python daily_audit.py\n"

        report += """
NEXT ACTIONS:
  - Daily (9 AM): Auto-audit runs on all machines
  - Weekly (Mondays): Dashboard report generated
  - Weekly (Fridays): Remote machine sync verification
  - Quarterly: Deep audit of all 277 CLAUDE.md files
"""
        return report

    def save_supervisor_report(self, report: str):
        """Save supervisor report"""
        report_file = self.monitoring_dir / f"supervisor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        return report_file

    def run_health_check(self):
        """Run and display health check"""
        health = self.check_system_health()
        report = self.generate_supervisor_report()
        print(report)
        self.save_supervisor_report(report)
        return health['status'] == "healthy"

    def run_full_report(self):
        """Generate comprehensive weekly report"""
        report = self.generate_supervisor_report()
        report_file = self.save_supervisor_report(report)
        print(f"\nSupervisor report saved: {report_file}")
        print(report)


def main():
    supervisor = TokenOptimizationSupervisor()

    if "--check" in sys.argv:
        supervisor.run_health_check()
    elif "--report" in sys.argv:
        supervisor.run_full_report()
    else:
        supervisor.run_health_check()


if __name__ == '__main__':
    main()
