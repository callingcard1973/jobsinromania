#!/usr/bin/env python3
import csv, json, re, os, sys, requests, hashlib, urllib.parse, time
from datetime import datetime, timedelta
from pathlib import Path

# Config
# Try raspibig path first, then Windows path
ANOFM_CSV = "/opt/ACTIVE/DELIVERY/companies_deep_enriched.csv" if os.path.exists("/opt/ACTIVE/DELIVERY/companies_deep_enriched.csv") else "D:/MEMORY/CLAUDE/DELIVERY/companies_deep_enriched.csv"
RASPIBIG_LLM = "http://192.168.100.20:11434/api/generate"
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
CPANEL_USER = "loaiidil"
APPLY_URL = "https://interjob.ro/apply.html"

SECTOR_DOMAINS = {
    "SECURITY_GUARDS": "careworkers.eu",
    "WAREHOUSE": "warehouseworkers.eu",
    "FACTORY": "factoryjobs.eu",
    "CONSTRUCTION": "buildjobs.eu",
    "ELECTRICIAN": "electricjobs.eu",
    "FARM": "farmworkers.eu",
    "HORECA": "horecaworkers.eu",
    "MEAT": "meatworkers.eu",
    "MECHANIC": "mechanicjobs.eu",
    "DRIVERS_DELIVERY": "mivromania.info",
}

def load_anofm_data():
    """Load and filter ANOFM CSV, rotating sectors each run."""
    try:
        with open(ANOFM_CSV, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [r for r in reader if r.get('best_email') and r.get('job_titles') and r.get('salary')]
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []

def sector_matches(job_categories, sector_key):
    """Check if job categories match sector."""
    cats = (job_categories or "").upper()
    return sector_key in cats or sector_key.replace("_", "") in cats.replace("_", "")

def generate_description(company, job_title, salary, location, retries=3):
    """Generate job description via Qwen LLM on raspibig."""
    prompt = f"""Generate a compelling 300-word job description for:
Company: {company}
Job Title: {job_title}
Salary: {salary}
Location: {location}

Include: requirements (skills, experience), benefits, work environment, why apply."""

    for attempt in range(retries):
        try:
            resp = requests.post(RASPIBIG_LLM, json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False}, timeout=30)
            if resp.status_code == 200:
                return resp.json().get('response', '').strip()
        except Exception as e:
            print(f"  LLM retry {attempt+1}/{retries}: {e}")
            time.sleep(2)
    return f"Join {company} as a {job_title}. Salary: {salary}. Location: {location}. Apply now!"

def create_job_html(job_id, company, title, salary, location, description, domain):
    """Create JSON-LD + HTML job listing."""
    schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": description,
        "hiringOrganization": {"@type": "Organization", "name": company},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": location}},
        "baseSalary": {"@type": "PriceSpecification", "currency": "RON", "priceCurrency": "RON", "price": str(salary)},
        "datePosted": datetime.now().isoformat(),
        "validThrough": (datetime.now() + timedelta(days=30)).isoformat(),
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} at {company}</title>
    <meta name="description" content="{description[:160]}">
    <script type="application/ld+json">{json.dumps(schema)}</script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .job-header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .salary {{ color: #27ae60; font-weight: bold; font-size: 1.2em; }}
        .apply-btn {{ background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
        .apply-btn:hover {{ background: #2980b9; }}
    </style>
</head>
<body>
    <div class="job-header">
        <h1>{title}</h1>
        <p><strong>Company:</strong> {company}</p>
        <p><strong>Location:</strong> {location}</p>
        <p class="salary"><strong>Salary:</strong> {salary} RON/month</p>
    </div>
    <h2>Job Description</h2>
    <p>{description}</p>
    <a href="{APPLY_URL}" class="apply-btn">Apply Now</a>
</body>
</html>"""
    return html

def deploy_to_cpanel(domain, job_id, html_content):
    """Deploy HTML to A2 cPanel via API."""
    try:
        path = f"/{domain}/jobs/{job_id}.html"
        api_url = f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file"
        params = {
            "cpanel_jsonapi_apiversion": 2,
            "cpanel_jsonapi_user": CPANEL_USER,
            "api_token": CPANEL_TOKEN,
            "dir": f"/home/{CPANEL_USER}/public_html{path}",
            "file_text": html_content,
        }
        resp = requests.post(api_url, params=params, verify=False, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"  cPanel deploy error: {e}")
        return False

def update_sitemap(domain, job_ids):
    """Update jobs_sitemap.xml on A2."""
    urls = [f"https://{domain}/jobs/{jid}.html" for jid in job_ids]
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(f'  <url><loc>{url}</loc><lastmod>{datetime.now().isoformat()}</lastmod></url>' for url in urls)}
</urlset>"""
    try:
        api_url = f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file"
        params = {
            "cpanel_jsonapi_apiversion": 2,
            "cpanel_jsonapi_user": CPANEL_USER,
            "api_token": CPANEL_TOKEN,
            "dir": f"/home/{CPANEL_USER}/public_html/{domain}/jobs_sitemap.xml",
            "file_text": xml,
        }
        return requests.post(api_url, params=params, verify=False, timeout=10).status_code == 200
    except:
        return False

def main():
    data = load_anofm_data()
    if not data:
        print(f"[{datetime.now()}] No ANOFM data found")
        return

    log_file = f"job_listings_{datetime.now().strftime('%Y-%m-%d')}.log"
    deployed_count = 0

    with open(log_file, "a") as log:
        log.write(f"\n[{datetime.now()}] Generator started\n")

        # Rotate through sectors (5-10 jobs per domain)
        for sector_key, domain in SECTOR_DOMAINS.items():
            jobs = [r for r in data if sector_matches(r.get('categories', ''), sector_key)][:8]

            for i, job in enumerate(jobs):
                try:
                    company = job['company']
                    title = (job['job_titles'] or 'Position').split('|')[0].strip()
                    salary = job['salary']
                    location = job.get('city', 'Romania')
                    job_id = hashlib.md5(f"{company}{title}{i}".encode()).hexdigest()[:12]

                    desc = generate_description(company, title, salary, location)
                    html = create_job_html(job_id, company, title, salary, location, desc, domain)

                    if deploy_to_cpanel(domain, job_id, html):
                        deployed_count += 1
                        log.write(f"[OK] {domain}: {company} - {title} (ID: {job_id})\n")
                        # Write to DB
                        try:
                            import sys, os
                            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                            from db_client import get_conn, safe_insert
                            conn = get_conn()
                            if conn:
                                sql = """
                                    INSERT INTO job_listings (job_id, domain, company, title, salary, location, description, deployed, date_posted, valid_through)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (job_id) DO UPDATE SET
                                        deployed = EXCLUDED.deployed,
                                        date_posted = EXCLUDED.date_posted,
                                        valid_through = EXCLUDED.valid_through
                                """
                                params = (job_id, domain, company, title, salary, location, desc, True, datetime.now(), datetime.now() + timedelta(days=30))
                                safe_insert(conn, sql, params)
                                conn.close()
                        except ImportError:
                            pass
                    else:
                        log.write(f"[ERR] {domain}: Failed to deploy {company}\n")
                except Exception as e:
                    log.write(f"[ERR] Error processing {job.get('company', 'Unknown')}: {e}\n")

        # Update sitemaps
        for domain in set(SECTOR_DOMAINS.values()):
            if update_sitemap(domain, []):
                log.write(f"[OK] Sitemap updated: {domain}\n")

        log.write(f"[{datetime.now()}] Complete - {deployed_count} jobs deployed\n")
        print(f"[{datetime.now()}] Deployed {deployed_count} jobs. Log: {log_file}")

if __name__ == "__main__":
    main()
