#!/usr/bin/env python3
"""Build static HTML pages from jobs.json for GitHub Pages."""

import json
import os
import re
import unicodedata
from datetime import datetime
from collections import defaultdict
from typing import List, Dict


def slug(text: str) -> str:
    """Convert text to URL-safe slug (handles Romanian characters)."""
    # Transliterate Romanian characters
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'ö': 'o', 'ü': 'u', 'ç': 'c', 'é': 'e',
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
        text = text.replace(char.upper(), repl.upper())

    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_FILE = os.path.join(OUTPUT_DIR, "data", "jobs.json")
PAGES_DIR = os.path.join(OUTPUT_DIR, "docs")

# Colors (buildJobs style)
COLOR_PRIMARY = "#e65100"
COLOR_TEXT = "#333"
COLOR_BG = "#f5f5f5"


def load_jobs() -> List[Dict]:
    """Load jobs from JSON."""
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("jobs", [])


def group_by_sector(jobs: List[Dict]) -> Dict[str, List[Dict]]:
    """Group jobs by sector."""
    groups = defaultdict(list)
    for job in jobs:
        sector = job.get("sector", "general").lower()
        groups[sector].append(job)
    return dict(groups)


def group_by_city(jobs: List[Dict]) -> Dict[str, List[Dict]]:
    """Group jobs by city."""
    groups = defaultdict(list)
    for job in jobs:
        city = job.get("city", "Romania").strip()
        groups[city].append(job)
    return dict(groups)


def format_job_card(job: Dict) -> str:
    """HTML card for single job."""
    title = job.get("title", "")
    city = job.get("city", "")
    sector = job.get("sector", "").title() if job.get("sector") else "General"
    salary = job.get("salary", "")
    contract = job.get("contract", "").title() if job.get("contract") else ""
    posted = job.get("posted", "")[:10] if job.get("posted") else ""

    salary_html = f"<span class='salary'>{salary}</span>" if salary else ""
    contract_html = f"<span class='contract'>{contract}</span>" if contract else ""

    return f"""
    <div class='job-card'>
      <div class='job-header'>
        <h3>{title}</h3>
        <span class='sector' style='background:{COLOR_PRIMARY}'>{sector}</span>
      </div>
      <div class='job-meta'>
        <span class='city'>{city}</span>
        {contract_html}
      </div>
      <div class='job-details'>
        {salary_html}
        <span class='posted'>{posted}</span>
      </div>
    </div>
    """


def html_header(title: str) -> str:
    """Page header HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - JobsInRomania</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {COLOR_BG}; color: {COLOR_TEXT}; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        header {{ background: {COLOR_PRIMARY}; color: white; padding: 30px 20px; text-align: center; margin-bottom: 30px; }}
        header h1 {{ font-size: 2em; margin-bottom: 10px; }}
        header p {{ font-size: 1.1em; opacity: 0.95; }}
        .nav {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; justify-content: center; }}
        .nav a {{ color: {COLOR_PRIMARY}; text-decoration: none; padding: 8px 16px; border: 1px solid {COLOR_PRIMARY}; border-radius: 4px; transition: all 0.3s; }}
        .nav a:hover {{ background: {COLOR_PRIMARY}; color: white; }}
        .nav a.active {{ background: {COLOR_PRIMARY}; color: white; }}
        .jobs-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
        .job-card {{ background: white; border-left: 4px solid {COLOR_PRIMARY}; padding: 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .job-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        .job-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px; }}
        .job-header h3 {{ flex: 1; color: {COLOR_PRIMARY}; font-size: 1.2em; }}
        .sector {{ font-size: 0.75em; padding: 4px 8px; border-radius: 3px; color: white; white-space: nowrap; }}
        .job-meta {{ display: flex; gap: 12px; margin: 12px 0; font-size: 0.9em; flex-wrap: wrap; }}
        .company, .city {{ color: #666; }}
        .job-details {{ display: flex; gap: 12px; margin-top: 12px; font-size: 0.85em; flex-wrap: wrap; }}
        .salary {{ color: #27ae60; font-weight: bold; }}
        .positions {{ color: #3498db; }}
        .posted {{ color: #999; }}
        .count {{ color: #666; font-size: 0.95em; margin: 20px 0; }}
        footer {{ text-align: center; margin-top: 40px; padding: 20px; color: #999; font-size: 0.9em; }}
        a {{ color: {COLOR_PRIMARY}; }}
    </style>
</head>
<body>
    <header>
        <h1>JobsInRomania</h1>
        <p>Daily job opportunities for workers in Romania</p>
    </header>
    <div class="container">
"""


def html_footer() -> str:
    """Page footer HTML."""
    return """
    </div>
    <footer>
        <p>Updated daily. Source: ANOFM. &copy; 2026 JobsInRomania.</p>
    </footer>
</body>
</html>
"""


def build_index(jobs: List[Dict]):
    """Build main index.html."""
    sectors = sorted(set(j.get("sector", "general") for j in jobs))
    cities = sorted(set(j.get("city", "Romania") for j in jobs if j.get("city")))

    html = html_header("Jobs in Romania")
    html += '<div class="nav">'
    html += '<a href="/" class="active">All Jobs</a>'
    for sector in sectors[:10]:
        html += f'<a href="/sectors/{sector.lower()}.html">{sector.title()}</a>'
    if len(sectors) > 10:
        html += f'<a href="/sectors/">+{len(sectors)-10} more</a>'
    html += '</div>'

    html += f'<p class="count">{len(jobs)} jobs available</p>'
    html += '<div class="jobs-grid">'
    for job in jobs[:100]:
        html += format_job_card(job)
    html += '</div>'
    html += '<p class="count" style="text-align:center">Browse by <a href="/sectors/">sector</a> or <a href="/cities/">city</a> for more jobs.</p>'
    html += html_footer()

    os.makedirs(os.path.join(PAGES_DIR), exist_ok=True)
    with open(os.path.join(PAGES_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def build_sector_pages(jobs: List[Dict]):
    """Build sector/*.html pages."""
    by_sector = group_by_sector(jobs)
    sectors = sorted(by_sector.keys())

    os.makedirs(os.path.join(PAGES_DIR, "sectors"), exist_ok=True)

    # Sector listing page
    listing_html = html_header("Jobs by Sector")
    listing_html += '<div class="nav"><a href="/">← Back</a></div>'
    listing_html += '<div class="jobs-grid">'
    for sector in sectors:
        count = len(by_sector[sector])
        listing_html += f'''<div class="job-card" style="text-align:center">
            <h3 style="color:{COLOR_PRIMARY}">{sector.title()}</h3>
            <p class="count">{count} jobs</p>
            <a href="/sectors/{sector.lower()}.html" style="color:{COLOR_PRIMARY};text-decoration:underline">View all →</a>
        </div>'''
    listing_html += '</div>'
    listing_html += html_footer()

    with open(os.path.join(PAGES_DIR, "sectors", "index.html"), "w", encoding="utf-8") as f:
        f.write(listing_html)

    # Individual sector pages
    for sector in sectors:
        sector_jobs = by_sector[sector]
        html = html_header(f"{sector.title()} Jobs")
        html += f'<div class="nav"><a href="/sectors/">← Back</a> | <a href="/">← Home</a></div>'
        html += f'<p class="count">{len(sector_jobs)} jobs in {sector.title()}</p>'
        html += '<div class="jobs-grid">'
        for job in sector_jobs:
            html += format_job_card(job)
        html += '</div>'
        html += html_footer()

        with open(os.path.join(PAGES_DIR, "sectors", f"{sector.lower()}.html"), "w", encoding="utf-8") as f:
            f.write(html)


def build_city_pages(jobs: List[Dict]):
    """Build cities/*.html pages."""
    by_city = group_by_city(jobs)
    cities = sorted(by_city.keys())

    os.makedirs(os.path.join(PAGES_DIR, "cities"), exist_ok=True)

    # City listing page
    listing_html = html_header("Jobs by City")
    listing_html += '<div class="nav"><a href="/">← Back</a></div>'
    listing_html += '<div class="jobs-grid">'
    for city in cities[:50]:
        count = len(by_city[city])
        city_slug = city.lower().replace(" ", "-")
        listing_html += f'''<div class="job-card" style="text-align:center">
            <h3 style="color:{COLOR_PRIMARY}">{city}</h3>
            <p class="count">{count} jobs</p>
            <a href="/cities/{city_slug}.html" style="color:{COLOR_PRIMARY};text-decoration:underline">View all →</a>
        </div>'''
    listing_html += '</div>'
    listing_html += html_footer()

    with open(os.path.join(PAGES_DIR, "cities", "index.html"), "w", encoding="utf-8") as f:
        f.write(listing_html)

    # Individual city pages
    for city in cities:
        city_jobs = by_city[city]
        city_slug = slug(city)
        html = html_header(f"Jobs in {city}")
        html += f'<div class="nav"><a href="/cities/">← Back</a> | <a href="/">← Home</a></div>'
        html += f'<p class="count">{len(city_jobs)} jobs in {city}</p>'
        html += '<div class="jobs-grid">'
        for job in city_jobs:
            html += format_job_card(job)
        html += '</div>'
        html += html_footer()

        with open(os.path.join(PAGES_DIR, "cities", f"{city_slug}.html"), "w", encoding="utf-8") as f:
            f.write(html)


def main():
    jobs = load_jobs()
    if not jobs:
        print("No jobs found in data/jobs.json")
        return

    build_index(jobs)
    build_sector_pages(jobs)
    build_city_pages(jobs)

    print(f"Generated HTML pages for {len(jobs)} jobs in {PAGES_DIR}/")


if __name__ == "__main__":
    main()
