#!/usr/bin/env python3
"""
Bulgaria Multi-Category Campaign Generator
Skill: Create campaigns for any Bulgarian industry category dynamically
Features: Query all categories, generate campaign configs, batch setup

Usage:
  python3 bulgaria_multi_category_campaign.py --list
  python3 bulgaria_multi_category_campaign.py --analyze
  python3 bulgaria_multi_category_campaign.py --create --category metalurzhiya --limit 300
  python3 bulgaria_multi_category_campaign.py --create-all --batch 10
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import re

# PostgreSQL
PG_HOST = 'localhost'
PG_DATABASE = 'interjob_master'
PG_USER = 'tudor'
PG_PASSWORD = 'tudor'

CAMPAIGNS_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
TEMPLATE_DIR = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/TEMPLATES')

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def connect_db():
    """Connect to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        print(f"✗ Connection failed: {e}")
        return None

def get_all_categories(conn):
    """Get all categories with email counts"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        sql = """
        SELECT
            category,
            COUNT(*) as total_emails,
            COUNT(DISTINCT email) as unique_emails,
            COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email
        FROM bg_business_catalog
        GROUP BY category
        ORDER BY total_emails DESC
        """
        cursor.execute(sql)
        categories = cursor.fetchall()
        cursor.close()
        return categories
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return []

def get_category_stats(conn, category):
    """Get detailed stats for single category"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        sql = """
        SELECT
            category,
            COUNT(*) as total,
            COUNT(DISTINCT email) as unique_emails,
            COUNT(DISTINCT city) as unique_cities,
            COUNT(DISTINCT name) as unique_companies,
            COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email,
            ROUND(100.0 * COUNT(CASE WHEN email IS NOT NULL THEN 1 END) / COUNT(*), 1) as email_hit_rate
        FROM bg_business_catalog
        WHERE category = %s
        GROUP BY category
        """
        cursor.execute(sql, (category,))
        stats = cursor.fetchone()
        cursor.close()
        return stats
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return None

def create_campaign_table(conn, campaign_name, category_list):
    """Create dedicated campaign table"""
    table_name = f"bg_{campaign_name.lower().replace('-', '_')}"

    cursor = conn.cursor()
    try:
        # Create table
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            email VARCHAR(254) NOT NULL UNIQUE,
            company VARCHAR(150),
            city VARCHAR(100),
            category VARCHAR(100),
            source VARCHAR(50),
            sent INTEGER DEFAULT 0,
            sent_at TIMESTAMP,
            method VARCHAR(20),
            bounced INTEGER DEFAULT 0,
            bounced_at TIMESTAMP,
            response INTEGER DEFAULT 0,
            response_at TIMESTAMP,
            error_msg TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(sql)

        # Create indexes
        for idx_name, col_name in [
            (f"idx_{campaign_name.lower().replace('-', '_')}_email", "email"),
            (f"idx_{campaign_name.lower().replace('-', '_')}_sent", "sent"),
            (f"idx_{campaign_name.lower().replace('-', '_')}_bounced", "bounced"),
            (f"idx_{campaign_name.lower().replace('-', '_')}_category", "category"),
        ]:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({col_name})")

        # Import contacts
        sql_import = f"""
        INSERT INTO {table_name} (email, company, city, category, source)
        SELECT DISTINCT
            b.email,
            b.name,
            b.city,
            b.category,
            'business_bg' as source
        FROM bg_business_catalog b
        WHERE b.category = ANY(%s)
        AND b.email IS NOT NULL
        AND b.email != ''
        ON CONFLICT (email) DO NOTHING
        """
        cursor.execute(sql_import, (category_list,))
        imported = cursor.rowcount

        conn.commit()
        cursor.close()

        return table_name, imported

    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        conn.rollback()
        cursor.close()
        return None, 0

# ============================================================================
# CAMPAIGN GENERATION
# ============================================================================

def create_campaign_folder(campaign_name):
    """Create campaign folder structure"""
    campaign_dir = CAMPAIGNS_DIR / f"BULGARIA_{campaign_name.upper()}"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    for subdir in ['templates', 'logs', 'contacts']:
        (campaign_dir / subdir).mkdir(exist_ok=True)

    return campaign_dir

def create_template_file(campaign_dir, campaign_name, subject_line):
    """Create email template for category"""
    template_content = f"""Subject: {subject_line}

Dear {{company}},

We are reaching out to {campaign_name.lower().replace('_', ' ')} companies from {{city}} and across Bulgaria with an exciting opportunity.

We connect qualified professionals from Bulgaria, Romania, and Moldova with legitimate job placements in Western Europe - Germany, Belgium, Netherlands, and more. Your team members remain employed by your company while working abroad, with full legal support, fair wages, and work permits handled.

This is an opportunity to:
- Keep your skilled workers employed at their home company
- Increase their income with Western European wages
- Build international experience and connections
- Expand your company's network across Europe

We have successfully placed professionals in industrial, manufacturing, technical, and service roles.

If your company has skilled teams interested in international opportunities, we'd like to discuss how this partnership could work for you.

To learn more about our business model and process, visit:
https://factoryjobs.eu/za-nas-bg/

Simply reply to this email with your questions or interest level. We're happy to discuss details.

Best regards,

Factory Jobs
InterJob Recruitment Team
office@factoryjobs.eu

---
To unsubscribe from future messages, please reply with "UNSUBSCRIBE" in the subject line.
"""

    template_path = campaign_dir / 'templates' / '01_inquiry.txt'
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template_content)

    return template_path

def create_campaign_config(campaign_name, category_list, table_name, contact_count):
    """Create campaign configuration file"""
    config = {
        "campaign_name": campaign_name,
        "categories": category_list,
        "database_table": table_name,
        "total_contacts": contact_count,
        "created_date": datetime.now().isoformat(),
        "sender_email": "office@factoryjobs.eu",
        "sender_name": "Factory Jobs",
        "daily_limit": 100,
        "delay_seconds": 360,
        "bounce_rate_threshold": 5.0,
        "scaling_path": [100, 300, 500],
        "status": "ready"
    }

    return config

def create_readme(campaign_dir, campaign_name, category_list, contact_count, config):
    """Create campaign README"""
    readme_content = f"""# Bulgaria {campaign_name.upper()} Campaign

## Overview

**Target**: {contact_count} companies across {len(category_list)} categories
**Sender**: office@factoryjobs.eu (factoryjobs.eu domain)
**Start Date**: {config['created_date'].split('T')[0]}
**Initial Rate**: 100 emails/day
**Scaling**: Up to 290/day if metrics look good

## Categories Included

{chr(10).join([f"- {cat}" for cat in category_list])}

## Running the Campaign

### Test Mode
```bash
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/BULGARIA_{campaign_name.upper()}
python3 send_{campaign_name.lower()}_industrial.py --test --limit 3
```

### Live Send
```bash
python3 send_{campaign_name.lower()}_industrial.py --limit 100
```

### Show Status
```bash
python3 send_{campaign_name.lower()}_industrial.py --status
```

### Resume Campaign
```bash
python3 send_{campaign_name.lower()}_industrial.py --resume --limit 100
```

## Database

**Table**: `{config['database_table']}`
**Total Contacts**: {contact_count}
**Categories**: {len(category_list)}

## Configuration

- Daily Limit: {config['daily_limit']}/day
- Delay: {config['delay_seconds']}s (6 minutes)
- Bounce Threshold: {config['bounce_rate_threshold']}%
- Failover: Brevo → A2 SMTP

## Next Steps

1. Deploy Bulgarian explainer page at factoryjobs.eu/za-nas-bg/
2. Run test mode to verify template and emails
3. Set Brevo API key: `export BREVO_INTERJOB_API_KEY='xkeysib-...'`
4. Start live campaign: `python3 send_*.py --limit 100`
5. Monitor metrics and scale up after 100 sent (if bounce <5%)

---

Created: {config['created_date']}
"""

    readme_path = campaign_dir / 'README.md'
    with open(readme_path, 'w') as f:
        f.write(readme_content)

    return readme_path

# ============================================================================
# COMMANDS
# ============================================================================

def cmd_list(args):
    """List all Bulgaria categories with stats"""
    print("\n" + "="*80)
    print("BULGARIA CATEGORIES - ALL INDUSTRIES")
    print("="*80)

    conn = connect_db()
    if not conn:
        return

    categories = get_all_categories(conn)
    conn.close()

    if not categories:
        print("No categories found")
        return

    print(f"\n{'Category':<40} {'Total':<8} {'Unique':<8} {'With Email':<12} {'Hit %':<8}")
    print("-"*80)

    for cat in categories:
        hit_rate = (cat['with_email'] / cat['total_emails'] * 100) if cat['total_emails'] > 0 else 0
        print(f"{cat['category']:<40} {cat['total_emails']:<8} {cat['unique_emails']:<8} {cat['with_email']:<12} {hit_rate:<8.1f}%")

    print("-"*80)
    print(f"Total: {len(categories)} categories, {sum(c['total_emails'] for c in categories)} records")
    print("="*80 + "\n")

def cmd_analyze(args):
    """Analyze category performance"""
    print("\n" + "="*80)
    print("BULGARIA CATEGORY ANALYSIS")
    print("="*80)

    conn = connect_db()
    if not conn:
        return

    categories = get_all_categories(conn)

    # Group by performance
    high_volume = [c for c in categories if c['with_email'] >= 50]
    medium_volume = [c for c in categories if 20 <= c['with_email'] < 50]
    low_volume = [c for c in categories if c['with_email'] < 20]

    print(f"\n✓ HIGH VOLUME ({len(high_volume)} categories, {sum(c['with_email'] for c in high_volume)} emails)")
    for cat in high_volume[:5]:
        print(f"  - {cat['category']}: {cat['with_email']} emails ({cat['total_emails']} records)")

    print(f"\n→ MEDIUM VOLUME ({len(medium_volume)} categories, {sum(c['with_email'] for c in medium_volume)} emails)")
    for cat in medium_volume[:5]:
        print(f"  - {cat['category']}: {cat['with_email']} emails")

    print(f"\n- LOW VOLUME ({len(low_volume)} categories, {sum(c['with_email'] for c in low_volume)} emails)")

    # Recommendations
    total_emails = sum(c['with_email'] for c in categories)
    print(f"\n📊 SUMMARY")
    print(f"  Total Categories: {len(categories)}")
    print(f"  Total Emails: {total_emails}")
    print(f"  High-Volume Campaigns Ready: {len(high_volume)}")
    print(f"  Recommended for Phase 2: {len([c for c in categories if c['with_email'] >= 30])}")

    print("\n📋 PHASE 2 RECOMMENDATION")
    print("  Top 10 categories by volume:")
    for i, cat in enumerate(categories[:10], 1):
        print(f"  {i}. {cat['category']}: {cat['with_email']} emails")

    conn.close()
    print("="*80 + "\n")

def cmd_create(args):
    """Create single category campaign"""
    if not args.category:
        print("✗ --category required")
        return

    print(f"\n✓ Creating campaign for: {args.category}")

    conn = connect_db()
    if not conn:
        return

    # Get category stats
    stats = get_category_stats(conn, args.category)
    if not stats:
        print(f"✗ Category not found: {args.category}")
        conn.close()
        return

    print(f"  Found: {stats['unique_emails']} unique emails, {stats['unique_cities']} cities")

    # Create campaign table
    table_name, imported = create_campaign_table(conn, args.category, [args.category])
    if not table_name:
        conn.close()
        return

    print(f"✓ Database table created: {table_name}")
    print(f"✓ Imported {imported} contacts")

    # Create folder structure
    campaign_dir = create_campaign_folder(args.category)
    print(f"✓ Campaign folder: {campaign_dir}")

    # Create template
    subject = f"Do You Have Skilled Teams for {args.category.replace('-', ' ').title()}?"
    template_path = create_template_file(campaign_dir, args.category, subject)
    print(f"✓ Template created: {template_path}")

    # Create config
    config = create_campaign_config(args.category, [args.category], table_name, imported)
    config_path = campaign_dir / 'config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, default=str)
    print(f"✓ Config created: {config_path}")

    # Create README
    readme_path = create_readme(campaign_dir, args.category, [args.category], imported, config)
    print(f"✓ README created: {readme_path}")

    conn.close()

    print(f"\n✓ Campaign ready: {campaign_dir}")
    print(f"  Next: cd {campaign_dir} && python3 send_{args.category.lower()}_industrial.py --test --limit 3")
    print()

def cmd_create_all(args):
    """Create campaigns for all high-volume categories"""
    print("\n" + "="*80)
    print("CREATING ALL HIGH-VOLUME CAMPAIGNS")
    print("="*80)

    conn = connect_db()
    if not conn:
        return

    categories = get_all_categories(conn)

    # Filter by min volume
    min_emails = args.min_emails or 30
    high_volume = [c for c in categories if c['with_email'] >= min_emails]

    print(f"\nFound {len(high_volume)} categories with ≥{min_emails} emails")
    print(f"Total emails to reach: {sum(c['with_email'] for c in high_volume)}")

    # Create campaigns
    created = 0
    for cat in high_volume:
        print(f"\n→ {cat['category']}: {cat['with_email']} emails")

        table_name, imported = create_campaign_table(conn, cat['category'], [cat['category']])
        if not table_name:
            print(f"  ✗ Failed to create")
            continue

        campaign_dir = create_campaign_folder(cat['category'])
        subject = f"Do You Have Skilled Teams for {cat['category'].replace('-', ' ').title()}?"
        template_path = create_template_file(campaign_dir, cat['category'], subject)

        config = create_campaign_config(cat['category'], [cat['category']], table_name, imported)
        config_path = campaign_dir / 'config.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)

        readme_path = create_readme(campaign_dir, cat['category'], [cat['category']], imported, config)

        print(f"  ✓ Table: {table_name}")
        print(f"  ✓ Folder: {campaign_dir}")
        print(f"  ✓ Imported: {imported}")
        created += 1

    conn.close()

    print(f"\n✓ Created {created} campaigns")
    print(f"  Total contacts: {sum(c['with_email'] for c in high_volume[:created])}")
    print("="*80 + "\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Bulgaria Multi-Category Campaign Generator'
    )

    subparsers = parser.add_subparsers(dest='command')

    # List command
    list_parser = subparsers.add_parser('list', help='List all categories')
    list_parser.set_defaults(func=cmd_list)

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze categories')
    analyze_parser.set_defaults(func=cmd_analyze)

    # Create single campaign
    create_parser = subparsers.add_parser('create', help='Create single campaign')
    create_parser.add_argument('--category', help='Category name')
    create_parser.set_defaults(func=cmd_create)

    # Create all campaigns
    create_all_parser = subparsers.add_parser('create-all', help='Create all campaigns')
    create_all_parser.add_argument('--min-emails', type=int, default=30, help='Min emails (default: 30)')
    create_all_parser.set_defaults(func=cmd_create_all)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
