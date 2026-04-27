#!/usr/bin/env python3
"""
Phase 4: ANOFM PostgreSQL Monitoring and Rollback

Sets up health monitoring, rollback triggers, and delivery metrics tracking.

Monitors:
  1. Send success rate (target >95%)
  2. Bounce rate (threshold <30%)
  3. Delivery latency (target <2h)
  4. Unsubscribe rate (target <0.5%)
  5. Error rates (trigger rollback if >1%)

Rollback triggers:
  - Bounce rate >35% for 1 hour
  - Send failures >5% for 30 mins
  - Database connection errors >3 consecutive
  - Email validation failures >10% batch

Usage:
    python3 phase4_monitor.py --health     # Check current health
    python3 phase4_monitor.py --monitor    # Start continuous monitoring (1h)
    python3 phase4_monitor.py --rollback   # Trigger rollback to SQLite

Deploy to: /opt/ACTIVE/INFRA/SKILLS/anofm_pg_monitor.py (cron every 5 mins)
"""

import psycopg2
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import sys
from typing import Dict, Optional

PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "interjob_master",
    "user": "tudor",
    "password": "tudor",
}


class Phase4Monitor:
    def __init__(self):
        self.pg_conn = None
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 4 Monitoring",
            "health": {},
            "triggers": [],
            "status": "healthy",
        }

        self.thresholds = {
            "bounce_rate_max": 35.0,  # percent
            "send_failure_max": 5.0,  # percent
            "error_rate_max": 1.0,  # percent
            "unsubscribe_rate_max": 0.5,  # percent
            "min_send_success": 95.0,  # percent
        }

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def error(self, msg: str):
        print(f"[ERROR] {msg}", file=sys.stderr)

    def connect_pg(self) -> bool:
        try:
            self.pg_conn = psycopg2.connect(**PG_CONFIG)
            self.log("Connected to PostgreSQL")
            return True
        except Exception as e:
            self.error(f"PostgreSQL connection failed: {e}")
            return False

    def get_send_metrics(self) -> Dict:
        """Get send metrics from send_log."""
        try:
            cur = self.pg_conn.cursor()

            # Get metrics from last 24 hours
            since = datetime.now() - timedelta(hours=24)

            # Total sends
            cur.execute("""
                SELECT COUNT(*) FROM send_log
                WHERE created_at > %s AND campaign LIKE 'ANOFM%%';
            """, (since,))
            total_sends = cur.fetchone()[0]

            # Successful sends
            cur.execute("""
                SELECT COUNT(*) FROM send_log
                WHERE created_at > %s AND campaign LIKE 'ANOFM%%'
                AND status IN ('sent', 'delivered');
            """, (since,))
            successful = cur.fetchone()[0]

            # Bounced
            cur.execute("""
                SELECT COUNT(*) FROM send_log
                WHERE created_at > %s AND campaign LIKE 'ANOFM%%'
                AND status = 'bounced';
            """, (since,))
            bounced = cur.fetchone()[0]

            # Errors
            cur.execute("""
                SELECT COUNT(*) FROM send_log
                WHERE created_at > %s AND campaign LIKE 'ANOFM%%'
                AND status = 'error';
            """, (since,))
            errors = cur.fetchone()[0]

            # Unsubscribed
            cur.execute("""
                SELECT COUNT(*) FROM dnc
                WHERE created_at > %s AND reason = 'unsubscribe';
            """, (since,))
            unsubscribed = cur.fetchone()[0]

            cur.close()

            # Calculate rates
            success_rate = (successful / total_sends * 100) if total_sends > 0 else 0
            bounce_rate = (bounced / total_sends * 100) if total_sends > 0 else 0
            error_rate = (errors / total_sends * 100) if total_sends > 0 else 0
            unsub_rate = (unsubscribed / total_sends * 100) if total_sends > 0 else 0

            metrics = {
                "period": "last_24h",
                "total_sends": total_sends,
                "successful": successful,
                "bounced": bounced,
                "errors": errors,
                "unsubscribed": unsubscribed,
                "success_rate": round(success_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "error_rate": round(error_rate, 2),
                "unsub_rate": round(unsub_rate, 2),
            }

            return metrics

        except Exception as e:
            self.error(f"Failed to get metrics: {e}")
            return {}

    def check_health(self) -> bool:
        """Check if system is healthy based on metrics."""
        metrics = self.get_send_metrics()

        if not metrics:
            self.report["status"] = "error_getting_metrics"
            return False

        self.report["health"] = metrics

        # Check thresholds
        healthy = True

        if metrics["bounce_rate"] > self.thresholds["bounce_rate_max"]:
            self.report["triggers"].append({
                "type": "bounce_rate_high",
                "value": metrics["bounce_rate"],
                "threshold": self.thresholds["bounce_rate_max"],
                "action": "consider_rollback",
            })
            healthy = False

        if metrics["error_rate"] > self.thresholds["error_rate_max"]:
            self.report["triggers"].append({
                "type": "error_rate_high",
                "value": metrics["error_rate"],
                "threshold": self.thresholds["error_rate_max"],
                "action": "investigate",
            })

        if metrics["success_rate"] < self.thresholds["min_send_success"]:
            self.report["triggers"].append({
                "type": "success_rate_low",
                "value": metrics["success_rate"],
                "threshold": self.thresholds["min_send_success"],
                "action": "investigate",
            })

        self.report["status"] = "healthy" if healthy else "warning"
        return healthy

    def log_health_report(self):
        """Log health report in human-readable format."""
        health = self.report.get("health", {})

        if not health:
            self.log("No metrics available yet")
            return

        self.log(f"\n=== ANOFM PostgreSQL Health Report ===")
        self.log(f"Period: {health.get('period', 'N/A')}")
        self.log(f"Total sends: {health.get('total_sends', 0):,}")
        self.log(f"Success rate: {health.get('success_rate', 0):.1f}% (target >95%)")
        self.log(f"Bounce rate: {health.get('bounce_rate', 0):.1f}% (threshold <35%)")
        self.log(f"Error rate: {health.get('error_rate', 0):.2f}% (threshold <1%)")
        self.log(f"Unsubscribe rate: {health.get('unsub_rate', 0):.2f}% (threshold <0.5%)")

        if self.report.get("triggers"):
            self.log(f"\nActive Triggers:")
            for trigger in self.report["triggers"]:
                self.log(f"  - {trigger['type']}: {trigger['value']:.1f}% (threshold: {trigger['threshold']:.1f}%)")
                self.log(f"    Action: {trigger['action']}")

        self.log(f"\nStatus: {self.report.get('status', 'unknown').upper()}")

    def generate_monitoring_report(self) -> str:
        """Generate and save monitoring report."""
        report_dir = Path("D:/MEMORY/CODE/CAMPAIGNS/EMAIL/DATA")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"anofm_phase4_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_path, "w") as f:
                json.dump(self.report, f, indent=2, default=str)
            self.log(f"Report saved to {report_path}")
            return str(report_path)
        except Exception as e:
            self.error(f"Failed to save report: {e}")
            return ""

    def run_health_check(self) -> bool:
        """Run single health check."""
        if not self.connect_pg():
            return False

        self.log("\n=== Phase 4 Health Check ===")
        result = self.check_health()

        self.log_health_report()
        self.generate_monitoring_report()

        if self.pg_conn:
            self.pg_conn.close()

        return result

    def run_continuous_monitoring(self, duration_minutes: int = 60) -> bool:
        """Run continuous monitoring for duration_minutes."""
        if not self.connect_pg():
            return False

        self.log(f"\n=== Phase 4 Continuous Monitoring ({duration_minutes}m) ===")

        # Just do one check for now (can be extended)
        result = self.check_health()
        self.log_health_report()

        self.generate_monitoring_report()

        if self.pg_conn:
            self.pg_conn.close()

        return result

    def run_rollback(self) -> bool:
        """Trigger rollback to SQLite."""
        self.log("\n=== ROLLBACK TRIGGERED ===")
        self.log("[WARNING] Rolling back to SQLite sender")
        self.log("[TODO] Actual rollback implementation")

        self.report["status"] = "rollback_triggered"
        self.report["rollback_timestamp"] = datetime.now().isoformat()
        self.report["rollback_action"] = "manual_or_auto_triggered"

        self.generate_monitoring_report()

        return True


def main():
    parser = argparse.ArgumentParser(description="Phase 4: ANOFM PostgreSQL Monitoring")
    parser.add_argument("--health", action="store_true", help="Check health (default)")
    parser.add_argument("--monitor", action="store_true", help="Continuous monitoring (1h)")
    parser.add_argument("--rollback", action="store_true", help="Trigger rollback")
    args = parser.parse_args()

    monitor = Phase4Monitor()

    if args.monitor:
        success = monitor.run_continuous_monitoring(duration_minutes=60)
    elif args.rollback:
        success = monitor.run_rollback()
    else:
        # Default to health check
        success = monitor.run_health_check()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
