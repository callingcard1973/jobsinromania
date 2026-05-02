#!/usr/bin/env python3
"""
Tudor Industrial Companies Prioritizer
Prioritizes bigger industrial companies for Tudor's ANOFM campaign
Runs daily to ensure Tudor targets the largest industrial employers first
"""

import sqlite3
import psycopg2
import json
import logging
from datetime import datetime, timedelta
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TudorIndustrialPrioritizer:
    def __init__(self):
        self.anofm_db_config = {
            'host': 'localhost',
            'database': 'anofm',
            'user': 'tudor',
            'password': 'tudor'
        }
        self.tudor_campaign_db = '/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db'
        self.priority_log = '/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/logs/industrial_priority.log'

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.priority_log), exist_ok=True)

    def connect_anofm_db(self):
        """Connect to ANOFM PostgreSQL database"""
        return psycopg2.connect(**self.anofm_db_config)

    def connect_tudor_db(self):
        """Connect to Tudor's campaign SQLite database"""
        return sqlite3.connect(self.tudor_campaign_db)

    def get_industrial_companies(self):
        """Get industrial companies from ANOFM, ranked by size"""
        query = """
        SELECT
            company_name,
            company_address,
            company_city,
            email,
            phone,
            contact_person,
            COUNT(*) as job_count,
            COUNT(DISTINCT job_title) as position_variety,
            array_agg(DISTINCT sector) as sectors,
            MAX(created_at) as latest_posting,
            -- Size score: job count + position variety + recent activity
            (COUNT(*) * 2 + COUNT(DISTINCT job_title) +
             CASE WHEN MAX(created_at) > NOW() - INTERVAL '7 days' THEN 10 ELSE 0 END) as size_score
        FROM jobs
        WHERE (
            job_title ILIKE '%industri%' OR
            job_title ILIKE '%product%' OR
            job_title ILIKE '%manufactur%' OR
            job_title ILIKE '%fabric%' OR
            job_title ILIKE '%steel%' OR
            job_title ILIKE '%metal%' OR
            company_name ILIKE '%industri%' OR
            company_name ILIKE '%steel%' OR
            company_name ILIKE '%metal%' OR
            company_name ILIKE '%fabric%' OR
            company_name ILIKE '%prod%' OR
            company_name ILIKE '%manufactur%' OR
            company_name ILIKE '%group%' OR
            company_name ILIKE '%corp%' OR
            sector ILIKE '%industri%' OR
            sector ILIKE '%product%' OR
            sector ILIKE '%manufactur%'
        )
        AND company_name IS NOT NULL
        AND LENGTH(company_name) > 5
        GROUP BY company_name, company_address, company_city, email, phone, contact_person
        HAVING COUNT(*) >= 2  -- Companies with at least 2 job postings
        ORDER BY size_score DESC, job_count DESC
        LIMIT 500;
        """

        with self.connect_anofm_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_existing_contacts(self):
        """Get existing contacts from Tudor's campaign"""
        query = 'SELECT company, email, status FROM contacts WHERE status IN ("pending", "sent")'

        with self.connect_tudor_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return {(row[0], row[1]): row[2] for row in cursor.fetchall()}

    def prioritize_industrial_contacts(self):
        """Update Tudor's database to prioritize industrial companies"""
        logger.info('Starting industrial companies prioritization for Tudor')

        # Get industrial companies from ANOFM
        industrial_companies = self.get_industrial_companies()
        logger.info(f'Found {len(industrial_companies)} industrial companies')

        # Get existing contacts
        existing_contacts = self.get_existing_contacts()
        logger.info(f'Found {len(existing_contacts)} existing contacts in Tudor DB')

        new_industrial = []
        updated_priorities = []

        with self.connect_tudor_db() as conn:
            cursor = conn.cursor()

            for i, company in enumerate(industrial_companies):
                company_name = company['company_name']
                email = company['email'] if company['email'] else None

                # Create a unique key for comparison
                key = (company_name, email)

                if key not in existing_contacts:
                    # New industrial company - add to database
                    try:
                        cursor.execute("""
                            INSERT INTO contacts (
                                company, email, city, sector, source, status,
                                phone, contact_name, added_at,
                                first_name, last_name, position
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            company_name,
                            email,
                            company['company_city'],
                            'Industrial Priority',
                            'anofm_industrial',
                            'pending',
                            company['phone'],
                            company['contact_person'],
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            None,
                            None,
                            f'Industrial Contact (Score: {company["size_score"]})'
                        ))
                        new_industrial.append(company_name)
                    except Exception as e:
                        logger.warning(f'Failed to add {company_name}: {e}')

                else:
                    # Existing company - update priority if it's industrial
                    if existing_contacts[key] == 'pending':
                        cursor.execute("""
                            UPDATE contacts
                            SET sector = 'Industrial Priority',
                                position = ?,
                                source = 'anofm_industrial'
                            WHERE company = ? AND COALESCE(email, '') = COALESCE(?, '')
                        """, (
                            f'Industrial Contact (Score: {company["size_score"]})',
                            company_name,
                            email
                        ))
                        updated_priorities.append(company_name)

            conn.commit()

        # Log results
        summary = {
            'timestamp': datetime.now().isoformat(),
            'new_industrial_companies': len(new_industrial),
            'updated_priorities': len(updated_priorities),
            'total_industrial_analyzed': len(industrial_companies),
            'top_companies': [comp['company_name'] for comp in industrial_companies[:10]]
        }

        with open(self.priority_log, 'a') as f:
            f.write(json.dumps(summary) + '\n')

        logger.info(f'Prioritization complete: {len(new_industrial)} new, {len(updated_priorities)} updated')
        return summary

    def run_daily_prioritization(self):
        """Run the daily prioritization process"""
        try:
            logger.info('=== TUDOR INDUSTRIAL PRIORITIZATION STARTED ===')

            # Step 1: Prioritize industrial contacts
            summary = self.prioritize_industrial_contacts()

            # Step 2: Update campaign status
            status_file = '/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/status.json'
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status = json.load(f)

                status['last_industrial_update'] = datetime.now().isoformat()
                status['industrial_companies_added'] = summary['new_industrial_companies']
                status['prioritization_status'] = 'Industrial companies prioritized'

                with open(status_file, 'w') as f:
                    json.dump(status, f, indent=2)

            logger.info('=== TUDOR INDUSTRIAL PRIORITIZATION COMPLETED ===')
            return summary

        except Exception as e:
            logger.error(f'Prioritization failed: {e}')
            raise

if __name__ == '__main__':
    prioritizer = TudorIndustrialPrioritizer()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            # Show status
            print('Tudor Industrial Prioritizer Status')
            if os.path.exists(prioritizer.priority_log):
                with open(prioritizer.priority_log, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        latest = json.loads(lines[-1].strip())
                        print(f'Last run: {latest["timestamp"]}')
                        print(f'New companies: {latest["new_industrial_companies"]}')
                        print(f'Top companies: {", ".join(latest["top_companies"][:5])}')
        elif sys.argv[1] == '--dry-run':
            # Dry run mode
            companies = prioritizer.get_industrial_companies()
            print(f'Found {len(companies)} industrial companies')
            for i, comp in enumerate(companies[:10], 1):
                print(f'{i}. {comp["company_name"]} (Score: {comp["size_score"]}, Jobs: {comp["job_count"]})')
    else:
        # Run the prioritization
        result = prioritizer.run_daily_prioritization()
        print(f'Industrial prioritization complete: {result["new_industrial_companies"]} new companies added')