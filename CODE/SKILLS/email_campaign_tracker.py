#!/usr/bin/env python3
"""
Email Campaign Tracker - Track Brevo email metrics across all domains
Monitor sends, opens, clicks, bounces, unsubscribes per campaign/domain

Usage:
    python3 email_campaign_tracker.py --dashboard         # Full dashboard
    python3 email_campaign_tracker.py --domain buildjobs.eu  # Domain stats
    python3 email_campaign_tracker.py --today             # Today's activity
    python3 email_campaign_tracker.py --alerts            # Show issues

Examples:
    python3 email_campaign_tracker.py --dashboard --days 7
    python3 email_campaign_tracker.py --export csv
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# Load environment for API keys
ENV_FILE = Path('/opt/ACTIVE/SCRAPERS/EUROPE/.env')
RASPI_ENV_FILE = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')  # Backup location


@dataclass
class DomainStats:
    """Stats for a single domain."""
    domain: str
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    spam_reports: int = 0
    daily_limit: int = 290

    @property
    def open_rate(self) -> float:
        return (self.opened / self.delivered * 100) if self.delivered else 0

    @property
    def click_rate(self) -> float:
        return (self.clicked / self.opened * 100) if self.opened else 0

    @property
    def bounce_rate(self) -> float:
        return (self.bounced / self.sent * 100) if self.sent else 0

    @property
    def remaining_today(self) -> int:
        return max(0, self.daily_limit - self.sent)


@dataclass
class CampaignStats:
    """Stats for a campaign."""
    campaign_id: str
    name: str
    domain: str
    created: datetime
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    unique_opens: int = 0
    clicked: int = 0
    unique_clicks: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    status: str = "unknown"


class BrevoAPI:
    """Brevo API client."""

    BASE_URL = "https://api.brevo.com/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'api-key': api_key,
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request."""
        import urllib.request
        import urllib.parse

        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  API error: {e}")
            return None

    def get_account_info(self) -> Optional[Dict]:
        """Get account information."""
        return self._request('account')

    def get_email_stats(self, start_date: str, end_date: str) -> Optional[Dict]:
        """Get aggregate email statistics."""
        return self._request('smtp/statistics/aggregatedReport', {
            'startDate': start_date,
            'endDate': end_date
        })

    def get_campaigns(self, limit: int = 50, offset: int = 0) -> Optional[Dict]:
        """Get email campaigns."""
        return self._request('emailCampaigns', {
            'limit': limit,
            'offset': offset,
            'status': 'sent'
        })

    def get_campaign_stats(self, campaign_id: str) -> Optional[Dict]:
        """Get stats for a specific campaign."""
        return self._request(f'emailCampaigns/{campaign_id}')

    def get_transactional_stats(self, start_date: str, end_date: str) -> Optional[Dict]:
        """Get transactional email statistics."""
        return self._request('smtp/statistics/events', {
            'startDate': start_date,
            'endDate': end_date
        })


class EmailCampaignTracker:
    """Track email campaigns across all Brevo domains."""

    # Known domains and their API keys (loaded from .env)
    DOMAINS = [
        'buildjobs.eu',
        'factoryjobs.eu',
        'careworkers.eu',
        'mivromania.info',
        'mivromania.online',
        'cifn.info',
        'interjob.ro',
        'nepalezi.com',
    ]

    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.domain_stats: Dict[str, DomainStats] = {}
        self.campaigns: List[CampaignStats] = []

    def _load_api_keys(self) -> Dict[str, str]:
        """Load Brevo API keys from environment."""
        keys = {}

        for env_file in [ENV_FILE, RASPI_ENV_FILE]:
            if not env_file.exists():
                continue

            try:
                content = env_file.read_text()
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')

                        # Match domain-specific keys
                        for domain in self.DOMAINS:
                            domain_key = domain.replace('.', '_').upper()
                            if domain_key in key and 'API' in key.upper():
                                keys[domain] = value
                                break

                        # Also check for generic BREVO_API_KEY
                        if key == 'BREVO_API_KEY' and 'default' not in keys:
                            keys['default'] = value

            except Exception as e:
                print(f"  Warning: Cannot read {env_file}: {e}")

        return keys

    def get_domain_stats(self, domain: str, days: int = 1) -> Optional[DomainStats]:
        """Get stats for a specific domain."""
        api_key = self.api_keys.get(domain) or self.api_keys.get('default')
        if not api_key:
            return None

        api = BrevoAPI(api_key)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        stats = api.get_email_stats(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        if not stats:
            return None

        return DomainStats(
            domain=domain,
            sent=stats.get('requests', 0),
            delivered=stats.get('delivered', 0),
            opened=stats.get('opens', 0),
            clicked=stats.get('clicks', 0),
            bounced=stats.get('hardBounces', 0) + stats.get('softBounces', 0),
            unsubscribed=stats.get('unsubscribed', 0),
            spam_reports=stats.get('spamReports', 0),
        )

    def get_all_domain_stats(self, days: int = 1) -> Dict[str, DomainStats]:
        """Get stats for all domains."""
        print(f"Fetching stats for {len(self.DOMAINS)} domains...")

        for domain in self.DOMAINS:
            try:
                stats = self.get_domain_stats(domain, days)
                if stats:
                    self.domain_stats[domain] = stats
                    print(f"  ✓ {domain}: {stats.sent} sent")
                else:
                    print(f"  - {domain}: No API key or data")
            except Exception as e:
                print(f"  ✗ {domain}: {e}")

        return self.domain_stats

    def get_campaigns_list(self, domain: str = None, limit: int = 20) -> List[CampaignStats]:
        """Get recent campaigns."""
        campaigns = []

        domains_to_check = [domain] if domain else self.DOMAINS

        for d in domains_to_check:
            api_key = self.api_keys.get(d) or self.api_keys.get('default')
            if not api_key:
                continue

            api = BrevoAPI(api_key)
            result = api.get_campaigns(limit=limit)

            if result and 'campaigns' in result:
                for c in result['campaigns']:
                    try:
                        camp_stats = CampaignStats(
                            campaign_id=str(c.get('id', '')),
                            name=c.get('name', 'Unknown'),
                            domain=d,
                            created=datetime.fromisoformat(c.get('createdAt', '').replace('Z', '+00:00')),
                            sent=c.get('statistics', {}).get('sent', 0),
                            delivered=c.get('statistics', {}).get('delivered', 0),
                            opened=c.get('statistics', {}).get('viewed', 0),
                            unique_opens=c.get('statistics', {}).get('uniqueViews', 0),
                            clicked=c.get('statistics', {}).get('clickers', 0),
                            status=c.get('status', 'unknown')
                        )
                        campaigns.append(camp_stats)
                    except Exception:
                        pass

        self.campaigns = sorted(campaigns, key=lambda c: c.created, reverse=True)
        return self.campaigns

    def get_alerts(self) -> List[str]:
        """Check for issues that need attention."""
        alerts = []

        for domain, stats in self.domain_stats.items():
            # High bounce rate
            if stats.bounce_rate > 5:
                alerts.append(f"🔴 {domain}: High bounce rate ({stats.bounce_rate:.1f}%)")

            # Spam reports
            if stats.spam_reports > 0:
                alerts.append(f"🔴 {domain}: {stats.spam_reports} spam reports!")

            # Low open rate
            if stats.sent > 100 and stats.open_rate < 10:
                alerts.append(f"🟡 {domain}: Low open rate ({stats.open_rate:.1f}%)")

            # Approaching limit
            if stats.remaining_today < 50:
                alerts.append(f"🟡 {domain}: Only {stats.remaining_today} sends remaining today")

            # Unsubscribes
            if stats.unsubscribed > 10:
                alerts.append(f"🟡 {domain}: {stats.unsubscribed} unsubscribes")

        return alerts

    def generate_dashboard(self, days: int = 1) -> str:
        """Generate a full dashboard."""
        lines = []
        lines.append("=" * 70)
        lines.append("EMAIL CAMPAIGN DASHBOARD")
        lines.append(f"Period: Last {days} day(s) | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        # Summary
        total_sent = sum(s.sent for s in self.domain_stats.values())
        total_delivered = sum(s.delivered for s in self.domain_stats.values())
        total_opened = sum(s.opened for s in self.domain_stats.values())
        total_clicked = sum(s.clicked for s in self.domain_stats.values())
        total_bounced = sum(s.bounced for s in self.domain_stats.values())

        lines.append("\nOVERALL SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Total Sent:      {total_sent:,}")
        lines.append(f"  Delivered:       {total_delivered:,}")
        lines.append(f"  Opened:          {total_opened:,} ({total_opened/total_delivered*100:.1f}%)" if total_delivered else f"  Opened:          {total_opened:,}")
        lines.append(f"  Clicked:         {total_clicked:,}")
        lines.append(f"  Bounced:         {total_bounced:,}")

        # Per-domain breakdown
        lines.append("\nPER DOMAIN STATS")
        lines.append("-" * 70)
        lines.append(f"{'Domain':<20} {'Sent':>8} {'Open%':>8} {'Click%':>8} {'Bounce%':>8} {'Left':>8}")
        lines.append("-" * 70)

        for domain in sorted(self.domain_stats.keys()):
            stats = self.domain_stats[domain]
            lines.append(
                f"{domain:<20} {stats.sent:>8} {stats.open_rate:>7.1f}% "
                f"{stats.click_rate:>7.1f}% {stats.bounce_rate:>7.1f}% {stats.remaining_today:>8}"
            )

        # Alerts
        alerts = self.get_alerts()
        if alerts:
            lines.append("\nALERTS")
            lines.append("-" * 40)
            for alert in alerts:
                lines.append(f"  {alert}")

        # Recent campaigns
        if self.campaigns:
            lines.append("\nRECENT CAMPAIGNS")
            lines.append("-" * 70)
            for camp in self.campaigns[:10]:
                open_rate = (camp.opened / camp.delivered * 100) if camp.delivered else 0
                lines.append(
                    f"  {camp.created.strftime('%m/%d')} | {camp.name[:30]:<30} | "
                    f"{camp.sent} sent | {open_rate:.1f}% open"
                )

        lines.append("\n" + "=" * 70)
        return '\n'.join(lines)

    def export_csv(self, output_path: Path = None) -> Path:
        """Export stats to CSV."""
        if output_path is None:
            output_path = Path(f'/tmp/email_stats_{datetime.now().strftime("%Y%m%d")}.csv')

        lines = ['domain,sent,delivered,opened,clicked,bounced,unsubscribed,spam,open_rate,click_rate,bounce_rate']

        for domain, stats in self.domain_stats.items():
            lines.append(
                f"{domain},{stats.sent},{stats.delivered},{stats.opened},"
                f"{stats.clicked},{stats.bounced},{stats.unsubscribed},"
                f"{stats.spam_reports},{stats.open_rate:.2f},{stats.click_rate:.2f},{stats.bounce_rate:.2f}"
            )

        output_path.write_text('\n'.join(lines))
        return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Email Campaign Tracker')
    parser.add_argument('--dashboard', action='store_true', help='Full dashboard')
    parser.add_argument('--domain', help='Stats for specific domain')
    parser.add_argument('--today', action='store_true', help="Today's activity")
    parser.add_argument('--alerts', action='store_true', help='Show alerts only')
    parser.add_argument('--campaigns', action='store_true', help='List campaigns')
    parser.add_argument('--days', type=int, default=1, help='Days to look back')
    parser.add_argument('--export', choices=['csv', 'json'], help='Export format')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    tracker = EmailCampaignTracker()

    if args.domain:
        stats = tracker.get_domain_stats(args.domain, days=args.days)
        if stats:
            if args.json:
                print(json.dumps({
                    'domain': stats.domain,
                    'sent': stats.sent,
                    'delivered': stats.delivered,
                    'opened': stats.opened,
                    'clicked': stats.clicked,
                    'bounced': stats.bounced,
                    'open_rate': stats.open_rate,
                    'click_rate': stats.click_rate,
                    'bounce_rate': stats.bounce_rate,
                    'remaining': stats.remaining_today
                }, indent=2))
            else:
                print(f"\n{stats.domain} - Last {args.days} day(s)")
                print("-" * 40)
                print(f"  Sent:        {stats.sent}")
                print(f"  Delivered:   {stats.delivered}")
                print(f"  Opened:      {stats.opened} ({stats.open_rate:.1f}%)")
                print(f"  Clicked:     {stats.clicked} ({stats.click_rate:.1f}%)")
                print(f"  Bounced:     {stats.bounced} ({stats.bounce_rate:.1f}%)")
                print(f"  Remaining:   {stats.remaining_today}/{stats.daily_limit}")
        else:
            print(f"No data for {args.domain}")

    elif args.campaigns:
        campaigns = tracker.get_campaigns_list(limit=20)
        if args.json:
            print(json.dumps([{
                'id': c.campaign_id,
                'name': c.name,
                'domain': c.domain,
                'sent': c.sent,
                'opened': c.opened,
                'status': c.status
            } for c in campaigns], indent=2))
        else:
            print("\nRecent Campaigns")
            print("-" * 60)
            for c in campaigns:
                print(f"  {c.created.strftime('%Y-%m-%d')} | {c.name[:35]:<35} | {c.sent} sent")

    elif args.alerts:
        tracker.get_all_domain_stats(days=args.days)
        alerts = tracker.get_alerts()
        if alerts:
            print("\nEMAIL ALERTS")
            print("-" * 40)
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("No alerts - all systems healthy")

    elif args.export:
        tracker.get_all_domain_stats(days=args.days)
        if args.export == 'csv':
            path = tracker.export_csv()
            print(f"Exported to: {path}")
        elif args.export == 'json':
            print(json.dumps({
                d: {
                    'sent': s.sent,
                    'delivered': s.delivered,
                    'opened': s.opened,
                    'clicked': s.clicked,
                    'open_rate': s.open_rate,
                    'click_rate': s.click_rate,
                    'bounce_rate': s.bounce_rate
                } for d, s in tracker.domain_stats.items()
            }, indent=2))

    elif args.dashboard or args.today:
        days = 1 if args.today else args.days
        tracker.get_all_domain_stats(days=days)
        tracker.get_campaigns_list(limit=10)
        print(tracker.generate_dashboard(days=days))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
