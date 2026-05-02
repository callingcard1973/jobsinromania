#!/usr/bin/env python3
"""
Proactive Alerts Skill - Monitor 24/7 and alert BEFORE failure
Predictive monitoring for scrapers, disk, memory, and data freshness

Usage:
    python3 proactive_alerts.py --check           # Run all checks
    python3 proactive_alerts.py --watch           # Continuous monitoring
    python3 proactive_alerts.py --status          # Show current status
    python3 proactive_alerts.py --test-telegram   # Test Telegram alert

Examples:
    python3 proactive_alerts.py --check --notify  # Check and send alerts
    python3 proactive_alerts.py --watch --interval 300  # Watch every 5 min
"""

import sys
import os
import subprocess
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

SCRAPERS_BASE = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE')
USB_DATA = Path('/mnt/hdd/SCRAPER_DATA')
ALERT_HISTORY_FILE = Path('/opt/ACTIVE/INFRA/SKILLS/.alert_history.json')


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """An alert to send."""
    level: AlertLevel
    category: str
    message: str
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ProactiveAlerts:
    """24/7 proactive monitoring and alerting."""

    # Thresholds
    DISK_WARNING_PERCENT = 80
    DISK_CRITICAL_PERCENT = 90
    MEMORY_WARNING_PERCENT = 80
    MEMORY_CRITICAL_PERCENT = 90
    DATA_STALE_HOURS = 48  # Alert if no new data in 48h
    DATA_CRITICAL_HOURS = 72  # Critical if no data in 72h
    FAILURE_RATE_WARNING = 0.3  # 30% failure rate
    FAILURE_RATE_CRITICAL = 0.5  # 50% failure rate

    def __init__(self, notify: bool = True):
        self.notify = notify
        self.alerts: List[Alert] = []
        self.alert_history = self._load_alert_history()

    def _load_alert_history(self) -> Dict:
        """Load alert history to avoid duplicate alerts."""
        try:
            if ALERT_HISTORY_FILE.exists():
                return json.loads(ALERT_HISTORY_FILE.read_text())
        except Exception:
            pass
        return {'sent': {}, 'last_check': None}

    def _save_alert_history(self):
        """Save alert history."""
        try:
            self.alert_history['last_check'] = datetime.now().isoformat()
            ALERT_HISTORY_FILE.write_text(json.dumps(self.alert_history, indent=2))
        except Exception:
            pass

    def _should_alert(self, alert_key: str, cooldown_hours: int = 4) -> bool:
        """Check if we should send this alert (avoid spam)."""
        last_sent = self.alert_history['sent'].get(alert_key)
        if not last_sent:
            return True
        try:
            last_time = datetime.fromisoformat(last_sent)
            return datetime.now() - last_time > timedelta(hours=cooldown_hours)
        except Exception:
            return True

    def _mark_alerted(self, alert_key: str):
        """Mark alert as sent."""
        self.alert_history['sent'][alert_key] = datetime.now().isoformat()
        self._save_alert_history()

    def check_disk_space(self) -> List[Alert]:
        """Check disk space on all mounts."""
        alerts = []

        try:
            result = subprocess.run(['df', '-h'], capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    usage_str = parts[4].rstrip('%')
                    mount = parts[5]

                    # Skip irrelevant mounts
                    if mount.startswith('/snap') or mount.startswith('/boot'):
                        continue

                    try:
                        usage = int(usage_str)
                        if usage >= self.DISK_CRITICAL_PERCENT:
                            alerts.append(Alert(
                                level=AlertLevel.CRITICAL,
                                category="disk",
                                message=f"DISK CRITICAL: {mount} at {usage}%",
                                details=f"Only {parts[3]} free on {mount}"
                            ))
                        elif usage >= self.DISK_WARNING_PERCENT:
                            alerts.append(Alert(
                                level=AlertLevel.WARNING,
                                category="disk",
                                message=f"Disk warning: {mount} at {usage}%",
                                details=f"{parts[3]} free on {mount}"
                            ))
                    except ValueError:
                        pass
        except Exception as e:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                category="disk",
                message=f"Cannot check disk space: {e}"
            ))

        return alerts

    def check_memory(self) -> List[Alert]:
        """Check memory usage."""
        alerts = []

        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 3:
                    total = int(parts[1])
                    used = int(parts[2])
                    usage_percent = (used / total) * 100

                    if usage_percent >= self.MEMORY_CRITICAL_PERCENT:
                        alerts.append(Alert(
                            level=AlertLevel.CRITICAL,
                            category="memory",
                            message=f"MEMORY CRITICAL: {usage_percent:.1f}% used",
                            details=f"{used}MB / {total}MB"
                        ))
                    elif usage_percent >= self.MEMORY_WARNING_PERCENT:
                        alerts.append(Alert(
                            level=AlertLevel.WARNING,
                            category="memory",
                            message=f"Memory warning: {usage_percent:.1f}% used",
                            details=f"{used}MB / {total}MB"
                        ))
        except Exception as e:
            pass

        return alerts

    def check_data_freshness(self) -> List[Alert]:
        """Check if scrapers are producing fresh data."""
        alerts = []
        now = datetime.now()

        csv_dir = USB_DATA / 'csv'
        if not csv_dir.exists():
            return alerts

        for country_dir in csv_dir.iterdir():
            if not country_dir.is_dir():
                continue

            # Find newest CSV
            csv_files = list(country_dir.glob('*.csv'))
            if not csv_files:
                continue

            newest = max(csv_files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(newest.stat().st_mtime)
            hours_old = (now - mtime).total_seconds() / 3600

            if hours_old >= self.DATA_CRITICAL_HOURS:
                alerts.append(Alert(
                    level=AlertLevel.CRITICAL,
                    category="data_freshness",
                    message=f"NO DATA: {country_dir.name} - {hours_old:.0f}h old",
                    details=f"Last: {newest.name} at {mtime.strftime('%Y-%m-%d %H:%M')}"
                ))
            elif hours_old >= self.DATA_STALE_HOURS:
                alerts.append(Alert(
                    level=AlertLevel.WARNING,
                    category="data_freshness",
                    message=f"Stale data: {country_dir.name} - {hours_old:.0f}h old",
                    details=f"Last: {newest.name}"
                ))

        return alerts

    def check_scraper_health(self) -> List[Alert]:
        """Check scraper failure rates."""
        alerts = []

        try:
            # Use health_monitor if available
            sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
            from health_monitor import ScraperHealthMonitor

            monitor = ScraperHealthMonitor(days=7)
            report = monitor.generate_report()

            for scraper in report.get('scrapers', []):
                name = scraper.get('name', 'unknown')
                success_rate = scraper.get('success_rate', 1.0)
                failure_rate = 1.0 - success_rate

                if failure_rate >= self.FAILURE_RATE_CRITICAL:
                    alerts.append(Alert(
                        level=AlertLevel.CRITICAL,
                        category="scraper_health",
                        message=f"SCRAPER FAILING: {name} ({failure_rate*100:.0f}% failures)",
                        details=f"Last 7 days: {scraper.get('total_runs', 0)} runs"
                    ))
                elif failure_rate >= self.FAILURE_RATE_WARNING:
                    alerts.append(Alert(
                        level=AlertLevel.WARNING,
                        category="scraper_health",
                        message=f"Scraper unhealthy: {name} ({failure_rate*100:.0f}% failures)",
                        details=f"Success rate: {success_rate*100:.0f}%"
                    ))
        except ImportError:
            pass
        except Exception as e:
            pass

        return alerts

    def check_pending_updates(self) -> List[Alert]:
        """Check for system updates."""
        alerts = []

        try:
            result = subprocess.run(
                ['apt-get', '-s', 'upgrade'],
                capture_output=True, text=True, timeout=30
            )
            # Count upgradeable packages
            upgrades = [l for l in result.stdout.split('\n') if l.startswith('Inst ')]
            if len(upgrades) > 20:
                alerts.append(Alert(
                    level=AlertLevel.INFO,
                    category="updates",
                    message=f"{len(upgrades)} system updates pending",
                    details="Run: sudo apt update && sudo apt upgrade"
                ))
        except Exception:
            pass

        return alerts

    def check_usb_mount(self) -> List[Alert]:
        """Check if USB is mounted."""
        alerts = []

        usb_mount = Path('/mnt/usb')
        if not usb_mount.is_mount() or not USB_DATA.exists():
            alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                category="usb",
                message="USB STORAGE NOT MOUNTED!",
                details="Data cannot be saved. Check /mnt/usb"
            ))

        return alerts

    def check_network(self) -> List[Alert]:
        """Check network connectivity."""
        alerts = []

        test_hosts = ['google.com', 'github.com']
        failed = []

        for host in test_hosts:
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '5', host],
                    capture_output=True, timeout=10
                )
                if result.returncode != 0:
                    failed.append(host)
            except Exception:
                failed.append(host)

        if len(failed) == len(test_hosts):
            alerts.append(Alert(
                level=AlertLevel.CRITICAL,
                category="network",
                message="NETWORK DOWN - Cannot reach internet",
                details=f"Failed to ping: {', '.join(failed)}"
            ))
        elif failed:
            alerts.append(Alert(
                level=AlertLevel.WARNING,
                category="network",
                message=f"Network issues - cannot reach {', '.join(failed)}",
                details="Partial connectivity"
            ))

        return alerts

    def check_cpu_temperature(self) -> List[Alert]:
        """Check CPU temperature (Raspberry Pi)."""
        alerts = []

        try:
            temp_file = Path('/sys/class/thermal/thermal_zone0/temp')
            if temp_file.exists():
                temp_mc = int(temp_file.read_text().strip())
                temp_c = temp_mc / 1000.0

                if temp_c >= 80:
                    alerts.append(Alert(
                        level=AlertLevel.CRITICAL,
                        category="temperature",
                        message=f"CPU OVERHEATING: {temp_c:.1f}C",
                        details="Throttling likely. Check cooling."
                    ))
                elif temp_c >= 70:
                    alerts.append(Alert(
                        level=AlertLevel.WARNING,
                        category="temperature",
                        message=f"CPU hot: {temp_c:.1f}C",
                        details="Consider improving cooling"
                    ))
        except Exception:
            pass

        return alerts

    def run_all_checks(self) -> List[Alert]:
        """Run all monitoring checks."""
        all_alerts = []

        checks = [
            ("USB Mount", self.check_usb_mount),
            ("Disk Space", self.check_disk_space),
            ("Memory", self.check_memory),
            ("Network", self.check_network),
            ("CPU Temperature", self.check_cpu_temperature),
            ("Data Freshness", self.check_data_freshness),
            ("Scraper Health", self.check_scraper_health),
        ]

        for name, check_func in checks:
            try:
                alerts = check_func()
                all_alerts.extend(alerts)
            except Exception as e:
                print(f"  Check {name} failed: {e}")

        self.alerts = all_alerts
        return all_alerts

    def send_telegram(self, message: str) -> bool:
        """Send Telegram notification."""
        try:
            from telegram_notifier import send_telegram_message
            return send_telegram_message(message)
        except ImportError:
            # Try direct API call
            try:
                env_file = Path('/opt/ACTIVE/SCRAPERS/EUROPE/.env')
                if env_file.exists():
                    import re
                    content = env_file.read_text()
                    token_match = re.search(r'TELEGRAM_BOT_TOKEN=([^\n]+)', content)
                    chat_match = re.search(r'TELEGRAM_CHAT_ID=([^\n]+)', content)

                    if token_match and chat_match:
                        import urllib.request
                        token = token_match.group(1).strip()
                        chat_id = chat_match.group(1).strip()
                        url = f"https://api.telegram.org/bot{token}/sendMessage"
                        data = json.dumps({'chat_id': chat_id, 'text': message}).encode()
                        req = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
                        urllib.request.urlopen(req, timeout=10)
                        return True
            except Exception as e:
                print(f"  Telegram failed: {e}")
        return False

    def notify_alerts(self, alerts: List[Alert]) -> int:
        """Send notifications for alerts (respecting cooldown)."""
        sent = 0

        for alert in alerts:
            alert_key = f"{alert.category}:{alert.message[:50]}"

            # Only notify for WARNING and CRITICAL
            if alert.level == AlertLevel.INFO:
                continue

            # Check cooldown
            cooldown = 1 if alert.level == AlertLevel.CRITICAL else 4
            if not self._should_alert(alert_key, cooldown_hours=cooldown):
                continue

            # Build message
            emoji = "🔴" if alert.level == AlertLevel.CRITICAL else "🟡"
            msg = f"{emoji} {alert.message}"
            if alert.details:
                msg += f"\n{alert.details}"

            if self.send_telegram(msg):
                self._mark_alerted(alert_key)
                sent += 1

        return sent

    def show_status(self) -> str:
        """Show current system status."""
        lines = []
        lines.append("=" * 60)
        lines.append("SYSTEM STATUS")
        lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)

        alerts = self.run_all_checks()

        if not alerts:
            lines.append("\n✓ All systems healthy - no alerts")
        else:
            critical = [a for a in alerts if a.level == AlertLevel.CRITICAL]
            warnings = [a for a in alerts if a.level == AlertLevel.WARNING]
            info = [a for a in alerts if a.level == AlertLevel.INFO]

            if critical:
                lines.append(f"\n🔴 CRITICAL ({len(critical)}):")
                for a in critical:
                    lines.append(f"  - {a.message}")

            if warnings:
                lines.append(f"\n🟡 WARNINGS ({len(warnings)}):")
                for a in warnings:
                    lines.append(f"  - {a.message}")

            if info:
                lines.append(f"\nℹ️  INFO ({len(info)}):")
                for a in info:
                    lines.append(f"  - {a.message}")

        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)

    def watch(self, interval_seconds: int = 300):
        """Continuous monitoring loop."""
        print(f"Starting proactive monitoring (interval: {interval_seconds}s)")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                alerts = self.run_all_checks()

                now = datetime.now().strftime('%H:%M:%S')
                critical = len([a for a in alerts if a.level == AlertLevel.CRITICAL])
                warnings = len([a for a in alerts if a.level == AlertLevel.WARNING])

                status = "✓ OK" if not critical and not warnings else f"🔴{critical} 🟡{warnings}"
                print(f"[{now}] {status}")

                if self.notify:
                    sent = self.notify_alerts(alerts)
                    if sent:
                        print(f"  Sent {sent} alert(s)")

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Proactive Alerts - 24/7 Monitoring')
    parser.add_argument('--check', action='store_true', help='Run all checks')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--notify', action='store_true', help='Send Telegram alerts')
    parser.add_argument('--interval', type=int, default=300, help='Watch interval (seconds)')
    parser.add_argument('--test-telegram', action='store_true', help='Test Telegram')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    monitor = ProactiveAlerts(notify=args.notify)

    if args.test_telegram:
        print("Testing Telegram...")
        if monitor.send_telegram("🧪 Test alert from proactive_alerts.py"):
            print("✓ Telegram working")
        else:
            print("✗ Telegram failed")
        sys.exit(0)

    if args.watch:
        monitor.watch(interval_seconds=args.interval)
    elif args.check or args.status:
        if args.json:
            alerts = monitor.run_all_checks()
            print(json.dumps([{
                'level': a.level.value,
                'category': a.category,
                'message': a.message,
                'details': a.details
            } for a in alerts], indent=2))
        else:
            print(monitor.show_status())

        if args.notify:
            sent = monitor.notify_alerts(monitor.alerts)
            print(f"\nSent {sent} alert(s)")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
