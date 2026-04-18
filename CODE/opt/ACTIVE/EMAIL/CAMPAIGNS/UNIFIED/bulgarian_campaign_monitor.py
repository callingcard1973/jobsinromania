#!/usr/bin/env python3
"""
Bulgarian Email Campaign Performance Monitor
Real-time tracking and analysis for Bulgarian campaigns
"""
import psycopg2
import json
import requests
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/bulgarian_monitor.log'),
        logging.StreamHandler()
    ]
)

class BulgarianCampaignMonitor:
    def __init__(self):
        load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')
        self.db_config = {
            'dbname': 'interjob_master',
            'user': 'tudor',
            'password': 'scraper123',
            'host': '/var/run/postgresql'
        }
        self.brevo_accounts = [
            {
                'name': 'BuildJobs',
                'api_key': os.getenv('BREVO_BUILDJOBS_API_KEY'),
                'email': 'office@buildjobs.eu',
                'daily_limit': 270,
                'sector': 'CONSTRUCTION'
            },
            {
                'name': 'Seicarescu',
                'api_key': os.getenv('BREVO_SEICARESCU_API_KEY'),
                'email': 'tudor@seicarescu.com',
                'daily_limit': 280,
                'sector': 'MANUFACTURING'
            },
            {
                'name': 'CareWorkers',
                'api_key': os.getenv('BREVO_CAREWORKERS_API_KEY'),
                'email': 'office@careworkers.eu',
                'daily_limit': 290,
                'sector': 'SERVICES'
            }
        ]

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_campaign_metrics(self):
        """Get real-time campaign metrics"""
        conn = self.get_db_connection()
        metrics = {}

        try:
            with conn.cursor() as cur:
                # BG_CAMPAIGN (Contractors) metrics
                cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN campaign_status IS NULL OR campaign_status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN campaign_status = 'sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN campaign_status = 'bounced' THEN 1 END) as bounced,
                    COUNT(CASE WHEN campaign_status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email
                FROM bg_campaign
                """)
                row = cur.fetchone()
                metrics['bg_contractors'] = {
                    'total': row[0],
                    'pending': row[1],
                    'sent': row[2],
                    'bounced': row[3],
                    'failed': row[4],
                    'with_email': row[5]
                }

                # A1_TRANSPORT_BULGARIA metrics
                cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN campaign_status IS NULL OR campaign_status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN campaign_status = 'sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN campaign_status = 'bounced' THEN 1 END) as bounced,
                    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email
                FROM a1_transport_bulgaria
                """)
                row = cur.fetchone()
                metrics['a1_transport'] = {
                    'total': row[0],
                    'pending': row[1],
                    'sent': row[2],
                    'bounced': row[3],
                    'with_email': row[4]
                }

                # Daily send statistics
                today = datetime.now().date()
                cur.execute("""
                SELECT
                    COUNT(*) as total_sent,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    sector,
                    sender
                FROM bg_send_log
                WHERE sent_at::date = %s
                GROUP BY sector, sender
                """, (today,))

                daily_sends = defaultdict(lambda: {'total': 0, 'successful': 0, 'failed': 0})
                for row in cur.fetchall():
                    sector = row[3] or 'unknown'
                    daily_sends[sector] = {
                        'total': row[0],
                        'successful': row[1],
                        'failed': row[2],
                        'sender': row[4]
                    }
                metrics['daily_sends'] = dict(daily_sends)

                # A1 Transport daily sends
                cur.execute("""
                SELECT
                    COUNT(*) as total_sent,
                    sender,
                    campaign
                FROM a1_transport_bulgaria_send_log
                WHERE sent_at::date = %s
                GROUP BY sender, campaign
                """, (today,))

                a1_daily = {}
                for row in cur.fetchall():
                    campaign = row[2] or 'A1_TRANSPORT'
                    a1_daily[campaign] = {
                        'total': row[0],
                        'sender': row[1]
                    }
                metrics['a1_daily_sends'] = a1_daily

                # Weekly performance
                week_ago = today - timedelta(days=7)
                cur.execute("""
                SELECT
                    DATE(sent_at) as send_date,
                    COUNT(*) as emails_sent,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as successful
                FROM bg_send_log
                WHERE sent_at::date >= %s
                GROUP BY DATE(sent_at)
                ORDER BY send_date
                """, (week_ago,))

                weekly_performance = []
                for row in cur.fetchall():
                    weekly_performance.append({
                        'date': row[0].strftime('%Y-%m-%d'),
                        'sent': row[1],
                        'successful': row[2],
                        'success_rate': round((row[2] / row[1]) * 100, 1) if row[1] > 0 else 0
                    })
                metrics['weekly_performance'] = weekly_performance

        finally:
            conn.close()

        return metrics

    def get_brevo_status(self):
        """Get Brevo account status and quota usage"""
        brevo_status = []

        for account in self.brevo_accounts:
            if not account['api_key']:
                continue

            headers = {
                'api-key': account['api_key'],
                'Content-Type': 'application/json'
            }

            status = {
                'name': account['name'],
                'email': account['email'],
                'daily_limit': account['daily_limit'],
                'sector': account['sector'],
                'status': 'unknown'
            }

            try:
                # Get account info
                response = requests.get(
                    'https://api.brevo.com/v3/account',
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    plan = data.get('plan', [{}])[0] if data.get('plan') else {}

                    status.update({
                        'status': 'active',
                        'credits_remaining': plan.get('credits', 0),
                        'plan_type': plan.get('type', 'unknown')
                    })

                    # Get today's usage
                    today = datetime.now().strftime('%Y-%m-%d')
                    stats_response = requests.get(
                        f'https://api.brevo.com/v3/smtp/statistics?startDate={today}&endDate={today}',
                        headers=headers,
                        timeout=10
                    )

                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        reports = stats_data.get('reports', [])
                        if reports:
                            today_stats = reports[0]
                            status.update({
                                'today_sent': today_stats.get('requests', 0),
                                'today_delivered': today_stats.get('delivered', 0),
                                'today_bounced': today_stats.get('hardBounces', 0) + today_stats.get('softBounces', 0),
                                'quota_used_pct': round((today_stats.get('requests', 0) / account['daily_limit']) * 100, 1)
                            })

                else:
                    status.update({
                        'status': 'error',
                        'error_code': response.status_code
                    })

            except Exception as e:
                status.update({
                    'status': 'connection_error',
                    'error': str(e)
                })

            brevo_status.append(status)

        return brevo_status

    def get_system_health(self):
        """Check system health indicators"""
        health = {}

        # Check orchestrator service
        try:
            result = os.popen('systemctl is-active unified-orchestrator.service').read().strip()
            health['orchestrator'] = result == 'active'
        except:
            health['orchestrator'] = False

        # Check database connectivity
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                health['database'] = True
            conn.close()
        except:
            health['database'] = False

        # Check disk space
        try:
            result = os.popen("df /opt | tail -1 | awk '{print $5}'").read().strip()
            health['disk_usage_pct'] = int(result.replace('%', ''))
        except:
            health['disk_usage_pct'] = 0

        return health

    def calculate_roi_metrics(self, metrics):
        """Calculate ROI and effectiveness metrics"""
        roi = {}

        # Total campaign reach
        total_contacts = metrics['bg_contractors']['total'] + metrics['a1_transport']['total']
        total_sent = metrics['bg_contractors']['sent'] + metrics['a1_transport']['sent']
        total_pending = metrics['bg_contractors']['pending'] + metrics['a1_transport']['pending']

        roi['total_contacts'] = total_contacts
        roi['total_sent'] = total_sent
        roi['total_pending'] = total_pending
        roi['campaign_progress_pct'] = round((total_sent / total_contacts) * 100, 1) if total_contacts > 0 else 0

        # Estimated completion date at 870 emails/day
        if total_pending > 0:
            days_remaining = total_pending / 870
            completion_date = datetime.now() + timedelta(days=days_remaining)
            roi['estimated_completion'] = completion_date.strftime('%Y-%m-%d')
            roi['days_remaining'] = round(days_remaining, 1)
        else:
            roi['estimated_completion'] = 'Complete'
            roi['days_remaining'] = 0

        # Weekly effectiveness
        weekly_total = sum(day['sent'] for day in metrics['weekly_performance'])
        weekly_successful = sum(day['successful'] for day in metrics['weekly_performance'])
        roi['weekly_success_rate'] = round((weekly_successful / weekly_total) * 100, 1) if weekly_total > 0 else 0

        return roi

    def generate_report(self):
        """Generate comprehensive monitoring report"""
        logging.info("Generating Bulgarian campaign monitoring report")

        metrics = self.get_campaign_metrics()
        brevo_status = self.get_brevo_status()
        system_health = self.get_system_health()
        roi_metrics = self.calculate_roi_metrics(metrics)

        report = {
            'timestamp': datetime.now().isoformat(),
            'campaign_metrics': metrics,
            'brevo_accounts': brevo_status,
            'system_health': system_health,
            'roi_metrics': roi_metrics
        }

        return report

    def print_status_dashboard(self):
        """Print formatted status dashboard"""
        report = self.generate_report()

        print("\n" + "="*80)
        print(f"🇧🇬 BULGARIAN CAMPAIGNS MONITORING DASHBOARD")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Campaign Overview
        print(f"\n📊 CAMPAIGN OVERVIEW:")
        bg = report['campaign_metrics']['bg_contractors']
        a1 = report['campaign_metrics']['a1_transport']
        roi = report['roi_metrics']

        print(f"   BG Contractors:    {bg['pending']:,} pending | {bg['sent']:,} sent | {bg['total']:,} total")
        print(f"   A1 Transport:      {a1['pending']:,} pending | {a1['sent']:,} sent | {a1['total']:,} total")
        print(f"   📈 Progress:       {roi['campaign_progress_pct']}% complete | {roi['days_remaining']} days remaining")
        print(f"   🎯 Est. Completion: {roi['estimated_completion']}")

        # Daily Performance
        print(f"\n📈 TODAY'S PERFORMANCE:")
        daily = report['campaign_metrics']['daily_sends']
        a1_daily = report['campaign_metrics']['a1_daily_sends']

        total_today = sum(sector['total'] for sector in daily.values())
        total_today += sum(sector['total'] for sector in a1_daily.values())

        if total_today > 0:
            print(f"   Total Sent Today:   {total_today} emails")
            for sector, data in daily.items():
                success_rate = round((data['successful'] / data['total']) * 100, 1) if data['total'] > 0 else 0
                print(f"   {sector:12}: {data['total']:3} sent | {success_rate}% success | {data['sender']}")
        else:
            print("   No emails sent today yet")

        # Brevo Account Status
        print(f"\n💳 BREVO ACCOUNTS STATUS:")
        total_quota_used = 0
        total_daily_limit = 0

        for account in report['brevo_accounts']:
            status_emoji = "✅" if account['status'] == 'active' else "❌"
            quota_used = account.get('today_sent', 0)
            quota_pct = account.get('quota_used_pct', 0)

            total_quota_used += quota_used
            total_daily_limit += account['daily_limit']

            print(f"   {status_emoji} {account['name']:12} ({account['sector']:13}): {quota_used:3}/{account['daily_limit']} ({quota_pct:4.1f}%)")

        overall_quota_pct = round((total_quota_used / total_daily_limit) * 100, 1)
        print(f"   📊 Overall Quota:   {total_quota_used}/{total_daily_limit} ({overall_quota_pct}%)")

        # System Health
        print(f"\n🔧 SYSTEM HEALTH:")
        health = report['system_health']

        orchestrator_status = "🟢 Running" if health['orchestrator'] else "🔴 Stopped"
        db_status = "🟢 Connected" if health['database'] else "🔴 Error"
        disk_emoji = "🟢" if health['disk_usage_pct'] < 80 else "🟡" if health['disk_usage_pct'] < 90 else "🔴"

        print(f"   Orchestrator:       {orchestrator_status}")
        print(f"   Database:          {db_status}")
        print(f"   Disk Usage:        {disk_emoji} {health['disk_usage_pct']}%")

        # Weekly Trends
        if report['campaign_metrics']['weekly_performance']:
            print(f"\n📊 WEEKLY TRENDS:")
            for day in report['campaign_metrics']['weekly_performance'][-7:]:
                print(f"   {day['date']}: {day['sent']:3} sent | {day['success_rate']:5.1f}% success")

        print("\n" + "="*80)

    def save_metrics_to_file(self, report):
        """Save metrics to JSON file for historical tracking"""
        metrics_dir = '/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/metrics'
        os.makedirs(metrics_dir, exist_ok=True)

        filename = f"bulgarian_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(metrics_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logging.info(f"Metrics saved to {filepath}")

def main():
    monitor = BulgarianCampaignMonitor()

    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--json':
        report = monitor.generate_report()
        print(json.dumps(report, indent=2, default=str))
    elif len(os.sys.argv) > 1 and os.sys.argv[1] == '--save':
        report = monitor.generate_report()
        monitor.save_metrics_to_file(report)
        print("Metrics saved to file")
    else:
        monitor.print_status_dashboard()

if __name__ == "__main__":
    main()