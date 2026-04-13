#!/usr/bin/env python3
"""
Search jobs by industry (factory/manufacturing), location, and required skills
Exports filtered results to: C:/Users/apami/OneDrive/Desktop/CATALOG JOBS
"""

import sys, os
import json
import csv
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from db_client import get_conn
except ImportError:
    print("[ERROR] Cannot import db_client")
    sys.exit(1)

# Output directory
CATALOG_DIR = Path("C:/Users/apami/OneDrive/Desktop/CATALOG JOBS")
CATALOG_DIR.mkdir(parents=True, exist_ok=True)

# Industry keywords
FACTORY_KEYWORDS = [
    'factory', 'manufacturing', 'production', 'assembly', 'industrial',
    'fabrication', 'metalworking', 'machinist', 'welding', 'welder',
    'technician', 'operator', 'cnc', 'lathe', 'drill'
]

# Romania domains
ROMANIA_DOMAINS = [
    'buildjobs.eu', 'electricjobs.eu', 'mechanicjobs.eu',
    'factoryjobs.eu', 'warehouseworkers.eu', 'interjob.ro'
]

def extract_skills(text):
    """Extract skills from job description"""
    if not text:
        return []

    text_lower = text.lower()
    skills = []

    # Common industrial skills
    skill_keywords = {
        'welding': ['weld', 'welder', 'arc', 'mig', 'tig'],
        'cnc': ['cnc', 'programming', 'machining'],
        'mechanical': ['mechanical', 'machine', 'equipment', 'assembly'],
        'electrical': ['electrical', 'wiring', 'circuit', 'voltage'],
        'hydraulic': ['hydraulic', 'pneumatic', 'pressure'],
        'troubleshooting': ['troubleshoot', 'diagnose', 'repair', 'maintenance'],
        'safety': ['safety', 'ppe', 'hazard', 'certification'],
        'quality': ['quality', 'inspection', 'control', 'standards'],
        'teamwork': ['team', 'collaboration', 'communicate'],
        'leadership': ['leader', 'supervisor', 'manage', 'oversee'],
    }

    for skill, keywords in skill_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                skills.append(skill)
                break

    return list(set(skills))  # Remove duplicates

def search_factory_jobs():
    """Search factory and manufacturing jobs in Romania"""
    conn = get_conn()
    if not conn:
        print("[ERROR] Cannot connect to database")
        return []

    try:
        cur = conn.cursor()

        # Get all jobs for Romanian factory/manufacturing companies
        cur.execute("""
            SELECT job_id, domain, company, title, salary, location, description,
                   deployed, date_posted, valid_through, created_at
            FROM job_listings
            WHERE (
                LOWER(domain) IN %s OR
                LOWER(title) SIMILAR TO '%%' || %s || '%%' OR
                LOWER(company) SIMILAR TO '%%' || %s || '%%' OR
                LOWER(description) SIMILAR TO '%%' || %s || '%%'
            )
            ORDER BY domain, company
        """, (
            tuple(ROMANIA_DOMAINS),
            '(factory|manufacturing|production|industrial|welding|mechanic)',
            '(factory|manufacturing|production|industrial|welding|mechanic)',
            '(factory|manufacturing|production|industrial|welding|mechanic)'
        ))

        rows = cur.fetchall()
        conn.close()
        return rows

    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        conn.close()
        return []

def export_factory_jobs_csv(jobs):
    """Export factory jobs to CSV with extracted skills"""
    if not jobs:
        print("[WARNING] No factory jobs found")
        return False

    csv_file = CATALOG_DIR / f"factory_jobs_romania_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"

    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Company', 'Title', 'Domain', 'Salary', 'Location',
                           'Required Skills', 'Description', 'Posted Date'])

            for row in jobs:
                job_id, domain, company, title, salary, location, desc, deployed, posted, valid, created = row
                skills = extract_skills(desc)
                skills_str = ', '.join(skills) if skills else 'Not specified'

                writer.writerow([
                    company,
                    title,
                    domain,
                    salary or 'Not specified',
                    location or 'Not specified',
                    skills_str,
                    desc[:200] if desc else '',
                    posted.date() if posted else ''
                ])

        print(f"[OK] CSV exported: {csv_file.name}")
        print(f"     {len(jobs)} jobs written")

        # Also update LATEST file
        latest_csv = CATALOG_DIR / "factory_jobs_romania_LATEST.csv"
        with open(latest_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Company', 'Title', 'Domain', 'Salary', 'Location',
                           'Required Skills', 'Description', 'Posted Date'])

            for row in jobs:
                job_id, domain, company, title, salary, location, desc, deployed, posted, valid, created = row
                skills = extract_skills(desc)
                skills_str = ', '.join(skills) if skills else 'Not specified'

                writer.writerow([
                    company,
                    title,
                    domain,
                    salary or 'Not specified',
                    location or 'Not specified',
                    skills_str,
                    desc[:200] if desc else '',
                    posted.date() if posted else ''
                ])

        return True

    except Exception as e:
        print(f"[ERROR] CSV export failed: {e}")
        return False

def export_factory_jobs_json(jobs):
    """Export factory jobs to JSON with extracted skills"""
    if not jobs:
        return False

    json_file = CATALOG_DIR / f"factory_jobs_romania_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"

    try:
        job_list = []
        for row in jobs:
            job_id, domain, company, title, salary, location, desc, deployed, posted, valid, created = row
            skills = extract_skills(desc)

            job = {
                'job_id': job_id,
                'company': company,
                'title': title,
                'domain': domain,
                'salary': salary,
                'location': location,
                'required_skills': skills,
                'description': desc,
                'posted_date': posted.isoformat() if posted else None,
            }
            job_list.append(job)

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_jobs': len(job_list),
                'industry': 'Factory & Manufacturing',
                'location': 'Romania',
                'jobs': job_list
            }, f, indent=2)

        print(f"[OK] JSON exported: {json_file.name}")

        # Also update LATEST file
        latest_json = CATALOG_DIR / "factory_jobs_romania_LATEST.json"
        with open(latest_json, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_jobs': len(job_list),
                'industry': 'Factory & Manufacturing',
                'location': 'Romania',
                'jobs': job_list
            }, f, indent=2)

        return True

    except Exception as e:
        print(f"[ERROR] JSON export failed: {e}")
        return False

def main():
    """Search and export factory/manufacturing jobs in Romania"""
    print(f"[INFO] Searching factory & manufacturing jobs in Romania...")
    print("=" * 70)

    jobs = search_factory_jobs()

    if not jobs:
        print("[WARNING] No jobs found matching criteria")
        return 1

    print(f"[OK] Found {len(jobs)} factory/manufacturing jobs")
    print("=" * 70)

    csv_ok = export_factory_jobs_csv(jobs)
    json_ok = export_factory_jobs_json(jobs)

    print("=" * 70)

    if csv_ok or json_ok:
        print("[OK] Factory jobs catalog complete")
        print(f"[INFO] Latest files: factory_jobs_romania_LATEST.csv, factory_jobs_romania_LATEST.json")
        return 0
    else:
        print("[ERROR] Export failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
