#!/usr/bin/env python3
"""
Compare Harghita scraped data with existing ANOFM database
"""

import psycopg2
import logging
from collections import defaultdict
from datetime import datetime
import json

class HarghitaComparator:
    def __init__(self):
        self.conn = None
        self.setup_logging()

    def setup_logging(self):
        log_file = "/opt/ACTIVE/SCRAPERS/HARGHITA/comparison.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                database="interjob_master",
                user="tudor",
                password="tudor"
            )
            self.logger.info("Connected to PostgreSQL")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def safe_query(self, query, params=None):
        """Safe database query"""
        try:
            cur = self.conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            result = cur.fetchall()
            cur.close()
            return result
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return None

    def analyze_harghita_data(self):
        """Analyze scraped Harghita data"""

        # Count PDFs by type
        pdf_stats = self.safe_query("""
            SELECT
                CASE
                    WHEN filename LIKE 'lmv_%' THEN 'Job Vacancy Stats'
                    WHEN filename LIKE 'Stimularea%' THEN 'Employer Incentives'
                    WHEN filename LIKE 'Prime%' THEN 'Employee Benefits'
                    WHEN filename LIKE 'Acte%' THEN 'Forms'
                    ELSE 'Other'
                END as pdf_type,
                COUNT(*) as count,
                SUM(file_size) as total_size
            FROM harghita_pdfs
            GROUP BY pdf_type
            ORDER BY count DESC
        """)

        # Count jobs by location
        location_stats = self.safe_query("""
            SELECT
                COALESCE(location, 'Unknown') as location,
                COUNT(*) as job_count
            FROM harghita_jobs
            WHERE location IS NOT NULL
            GROUP BY location
            ORDER BY job_count DESC
        """)

        # Job titles analysis
        title_stats = self.safe_query("""
            SELECT
                title,
                COUNT(*) as frequency
            FROM harghita_jobs
            WHERE title IS NOT NULL
            GROUP BY title
            ORDER BY frequency DESC
            LIMIT 20
        """)

        self.logger.info("=== HARGHITA DATA ANALYSIS ===")

        self.logger.info("PDF Categories:")
        if pdf_stats:
            for pdf_type, count, size in pdf_stats:
                size_mb = (size or 0) / (1024*1024)
                self.logger.info(f"  {pdf_type}: {count} files, {size_mb:.1f} MB")

        self.logger.info("Jobs by Location:")
        if location_stats:
            for location, count in location_stats:
                self.logger.info(f"  {location}: {count} jobs")

        self.logger.info("Top Job Titles:")
        if title_stats:
            for title, freq in title_stats:
                self.logger.info(f"  {title}: {freq} times")

        return {
            "pdf_stats": pdf_stats,
            "location_stats": location_stats,
            "title_stats": title_stats
        }

    def compare_with_anofm(self):
        """Compare with existing ANOFM data"""

        # Check if we have ANOFM data for Harghita
        anofm_companies = self.safe_query("""
            SELECT COUNT(*) FROM companies
            WHERE country = 'RO' AND (
                name ILIKE '%harghita%' OR
                address ILIKE '%harghita%' OR
                address ILIKE '%miercurea ciuc%' OR
                address ILIKE '%odorheiu%' OR
                address ILIKE '%gheorgheni%' OR
                address ILIKE '%toplita%'
            )
        """)

        # Check for existing Harghita contacts
        anofm_contacts = self.safe_query("""
            SELECT COUNT(*) FROM contacts
            WHERE address ILIKE ANY(ARRAY['%harghita%', '%miercurea ciuc%', '%odorheiu%', '%gheorgheni%', '%toplita%'])
        """)

        # Compare job categories
        harghita_job_types = self.safe_query("""
            SELECT
                CASE
                    WHEN title ILIKE '%muncitor%' THEN 'Worker'
                    WHEN title ILIKE '%operator%' THEN 'Operator'
                    WHEN title ILIKE '%inginer%' THEN 'Engineer'
                    WHEN title ILIKE '%tehnician%' THEN 'Technician'
                    WHEN title ILIKE '%sofer%' THEN 'Driver'
                    WHEN title ILIKE '%bucatar%' THEN 'Cook'
                    ELSE 'Other'
                END as job_category,
                COUNT(*) as count
            FROM harghita_jobs
            GROUP BY job_category
            ORDER BY count DESC
        """)

        self.logger.info("=== COMPARISON WITH ANOFM DATA ===")

        if anofm_companies:
            self.logger.info(f"ANOFM companies in Harghita area: {anofm_companies[0][0]}")

        if anofm_contacts:
            self.logger.info(f"ANOFM contacts in Harghita area: {anofm_contacts[0][0]}")

        self.logger.info("Harghita job categories:")
        if harghita_job_types:
            for category, count in harghita_job_types:
                self.logger.info(f"  {category}: {count}")

        return {
            "anofm_companies": anofm_companies[0][0] if anofm_companies else 0,
            "anofm_contacts": anofm_contacts[0][0] if anofm_contacts else 0,
            "job_categories": harghita_job_types
        }

    def generate_report(self):
        """Generate comprehensive comparison report"""

        report = {
            "generated_at": datetime.now().isoformat(),
            "harghita_analysis": self.analyze_harghita_data(),
            "anofm_comparison": self.compare_with_anofm()
        }

        # Save report to file
        report_file = "/opt/ACTIVE/SCRAPERS/HARGHITA/comparison_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Detailed report saved to: {report_file}")

        # Summary statistics
        total_pdfs = self.safe_query("SELECT COUNT(*) FROM harghita_pdfs")
        total_jobs = self.safe_query("SELECT COUNT(*) FROM harghita_jobs")

        self.logger.info("=== SUMMARY ===")
        self.logger.info(f"Total PDFs processed: {total_pdfs[0][0] if total_pdfs else 0}")
        self.logger.info(f"Total jobs extracted: {total_jobs[0][0] if total_jobs else 0}")

        return report

    def run(self):
        """Main comparison method"""
        self.logger.info("Starting Harghita data comparison")

        try:
            self.connect_db()
            report = self.generate_report()
            self.logger.info("Comparison complete")
            return report

        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    comparator = HarghitaComparator()
    comparator.run()