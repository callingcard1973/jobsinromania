#!/usr/bin/env python3
"""
CAP Federation Monitoring and Dashboard

Provides daily summaries, high-value alerts, and status monitoring via Telegram.
Uses existing alerting infrastructure.
"""

import sys
import psycopg2
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

try:
    from alerting import send_telegram
except ImportError:
    print("WARNING: alerting module not available - no Telegram alerts")
    send_telegram = None


# Configuration
DB_NAME = "interjob_master"
DB_USER = "tudor"
DB_HOST = "localhost"


def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(host=DB_HOST, user=DB_USER, database=DB_NAME)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


def get_cap_stats() -> Dict:
    """
    Fetch CAP federation statistics from database.

    Returns:
        Dict with all key metrics
    """
    stats = {"cooperatives": {}, "contracts": {}, "outreach": {}, "financials": {}}

    conn = connect_db()
    if not conn:
        return stats

    try:
        cursor = conn.cursor()

        # 1. Cooperative statistics
        cursor.execute("SELECT COUNT(*) FROM cap_cooperatives")
        stats["cooperatives"]["total"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cap_cooperatives WHERE status = 'MEMBER'")
        stats["cooperatives"]["members"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM cap_cooperatives WHERE status = 'PROSPECT'"
        )
        stats["cooperatives"]["prospects"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(capacity_annual_tons) FROM cap_cooperatives WHERE status = 'MEMBER'"
        )
        result = cursor.fetchone()[0]
        stats["cooperatives"]["total_capacity"] = float(result) if result else 0

        cursor.execute(
            "SELECT county, COUNT(*) as num, SUM(capacity_annual_tons) as capacity FROM cap_cooperatives WHERE status = 'MEMBER' GROUP BY county ORDER BY num DESC"
        )
        stats["cooperatives"]["by_county"] = dict(cursor.fetchall())

        # 2. Contract statistics
        cursor.execute("SELECT COUNT(*) FROM cap_contracts")
        stats["contracts"]["total"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cap_contracts WHERE status = 'BIDDING'")
        stats["contracts"]["bidding"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cap_contracts WHERE status = 'AWARDED'")
        stats["contracts"]["awarded"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(value_eur) FROM cap_contracts WHERE status = 'AWARDED'"
        )
        result = cursor.fetchone()[0]
        stats["contracts"]["total_value_eur"] = float(result) if result else 0

        cursor.execute(
            "SELECT SUM(value_eur * 0.08) FROM cap_contracts WHERE status = 'AWARDED'"
        )
        result = cursor.fetchone()[0]
        stats["contracts"]["cap_margin_eur"] = float(result) if result else 0

        # 3. Outreach statistics
        cursor.execute("SELECT COUNT(*) FROM cap_outreach_logs")
        stats["outreach"]["total_emails"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cap_outreach_logs WHERE opened = TRUE")
        stats["outreach"]["opened"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cap_outreach_logs WHERE replied = TRUE")
        stats["outreach"]["replied"] = cursor.fetchone()[0]

        # 4. Recent activity (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)

        cursor.execute(
            "SELECT COUNT(*) FROM cap_contracts WHERE award_date >= %s",
            (seven_days_ago,),
        )
        stats["contracts"]["awarded_last_7_days"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(value_eur * 0.08) FROM cap_contracts WHERE award_date >= %s",
            (seven_days_ago,),
        )
        result = cursor.fetchone()[0]
        stats["outreach"]["revenue_last_7_days"] = float(result) if result else 0

        cursor.close()

    except Exception as e:
        print(f"Error fetching stats: {e}")
    finally:
        if conn:
            conn.close()

    return stats


def get_high_value_opportunities(days_back: int = 7) -> List[Dict]:
    """
    Fetch high-value contract opportunities.

    Args:
        days_back: How far back to look for contracts

    Returns:
        List of high-value contracts (>= 50K EUR)
    """
    conn = connect_db()
    if not conn:
        return []

    contracts = []

    try:
        cursor = conn.cursor()

        # Query high-value contracts
        query = (
            """
            SELECT id, contract_name, buyer_name, value_eur, cpv_code, cpv_description,
                   buyer_type, status, created_at
            FROM cap_contracts
            WHERE value_eur >= 50000
              AND status IN ('OPPORTUNITY', 'BIDDING')
              AND created_at >= NOW() - INTERVAL '%s days'
            ORDER BY value_eur DESC
        """
            % days_back
        )

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]

        for row in cursor.fetchall():
            contract = dict(zip(columns, row))
            contracts.append(contract)

        cursor.close()

    except Exception as e:
        print(f"Error fetching opportunities: {e}")
    finally:
        if conn:
            conn.close()

    return contracts


def get_new_members(days_back: int = 30) -> List[Dict]:
    """
    Fetch recently signed members (LOI -> MEMBER).

    Args:
        days_back: How far back to look

    Returns:
        List of new members
    """
    conn = connect_db()
    if not conn:
        return []

    members = []

    try:
        cursor = conn.cursor()

        # Query new members
        query = (
            """
            SELECT id, name, county, capacity_annual_tons, products, email,
                   certification_status, status, updated_at
            FROM cap_cooperatives
            WHERE updated_at >= NOW() - INTERVAL '%s days'
              AND status = 'MEMBER'
            ORDER BY updated_at DESC
        """
            % days_back
        )

        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]

        for row in cursor.fetchall():
            member = dict(zip(columns, row))
            members.append(member)

        cursor.close()

    except Exception as e:
        print(f"Error fetching new members: {e}")
    finally:
        if conn:
            conn.close()

    return members


def format_daily_summary() -> str:
    """Format daily summary message for Telegram."""

    stats = get_cap_stats()

    message = f"""
📊 CAP Federation Daily Summary ({datetime.now():%Y-%m-%d})

🏭 Cooperatives:
   Total: {stats["cooperatives"]["total"]}
   Members: {stats["cooperatives"]["members"]} ({stats["cooperatives"]["total"] and int(stats["cooperatives"]["members"] / stats["cooperatives"]["total"] * 100) if stats["cooperatives"]["total"] else 0}%)
   Prospects: {stats["cooperatives"]["prospects"]}
   Total Capacity: {stats["cooperatives"].get("total_capacity", 0):,.0f} tons/year

   Top Counties:
"""

    # Add top 5 counties
    for county, data in list(stats["cooperatives"].get("by_county", {}).items())[:5]:
        if isinstance(data, tuple):
            num, capacity = data
            message += f"   {county}: {num} members, {capacity:,.0f} tons\n"

    message += f"""
💼 Contracts:
   Total: {stats["contracts"]["total"]}
   Bidding: {stats["contracts"]["bidding"]}
   Awarded: {stats["contracts"]["awarded"]}
   Total Value: {stats["contracts"].get("total_value_eur", 0):,.0f} EUR
   CAP Margin (Lifetime): {stats["contracts"].get("cap_margin_eur", 0):,.0f} EUR
   Last 7 Days: {stats["contracts"].get("awarded_last_7_days", 0)} awarded, {stats["outreach"].get("revenue_last_7_days", 0):,.0f} EUR margin

📧 Outreach:
   Total Emails: {stats["outreach"].get("total_emails", 0)}
   Opened: {stats["outreach"].get("opened", 0)}
   Replied: {stats["outreach"].get("replied", 0)}
   Response Rate: {((stats["outreach"].get("replied", 0) / stats["outreach"].get("total_emails", 1)) * 100) if stats["outreach"].get("total_emails", 0) > 0 else 0:.1f}%

🎯 Targets:
   15 Members: Month 4
   First Revenue: Week 6-7
   Year 1 Revenue: 650K-1.3M EUR
"""

    return message


def send_daily_summary():
    """Send daily summary to Telegram."""

    message = format_daily_summary()

    if send_telegram:
        send_telegram(message)
        print("✅ Daily summary sent to Telegram")
    else:
        print("\n" + message + "\n")


def send_high_value_alerts():
    """Alert on high-value contract opportunities (>= 100K EUR)."""

    contracts = get_high_value_opportunities(days_back=3)

    if not contracts:
        return

    # Filter for >= 100K EUR
    high_value = [c for c in contracts if c["value_eur"] >= 100000]

    if not high_value:
        return

    message = "💼 HIGH-VALUE CONTRACT OPPORTUNITIES\n\n"

    for contract in high_value:
        message += f"""
📋 {contract["contract_name"]}
   Value: {contract["value_eur"]:,.0f} EUR
   Buyer: {contract["buyer_name"]}
   Type: {contract["buyer_type"]}
   CPV: {contract["cpv_code"]} - {contract["cpv_description"]}
   Status: {contract["status"]}
   Created: {contract["created_at"]}
   
"""

    if send_telegram:
        send_telegram(message)
        print("✅ High-value alerts sent")
    else:
        print("\n" + message + "\n")


def send_new_member_alert():
    """Alert on new members signed (last 30 days)."""

    members = get_new_members(days_back=30)

    if not members:
        return

    message = f"🎉 {len(members)} NEW MEMBERS (Last 30 Days)\n\n"

    for member in members:
        message += f"""
✅ {member["name"]}
   County: {member["county"]}
   Capacity: {member.get("capacity_annual_tons", 0):,.0f} tons/year
   Products: {member.get("products", [])}
   Joined: {member["updated_at"]}
   
"""

    if send_telegram:
        send_telegram(message)
        print("✅ New member alerts sent")
    else:
        print("\n" + message + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CAP Monitoring")
    parser.add_argument("--daily", action="store_true", help="Send daily summary")
    parser.add_argument("--alerts", action="store_true", help="Send high-value alerts")
    parser.add_argument("--members", action="store_true", help="Send new member alerts")
    parser.add_argument("--all", action="store_true", help="Send all alerts")

    args = parser.parse_args()

    if args.daily or args.all:
        send_daily_summary()

    if args.alerts or args.all:
        send_high_value_alerts()

    if args.members or args.all:
        send_new_member_alert()

    if not any([args.daily, args.alerts, args.members, args.all]):
        # Default: show stats without sending
        print("\n" + format_daily_summary() + "\n")


if __name__ == "__main__":
    main()
