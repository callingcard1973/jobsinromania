#!/usr/bin/env python3
"""Build single index.html page with all jobs (client-side searchable)."""

import json
import os
from datetime import datetime
from typing import List, Dict

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
    sector_tag = f"<span class='sector'>{sector}</span>"

    return f"""    <div class='job-card'>
      <div class='job-header'>
        <h3>{title}</h3>
        {sector_tag}
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


def build_index(jobs: List[Dict]):
    """Build single searchable index.html with all jobs."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jobs in Romania - JobsInRomania</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: {COLOR_BG}; color: {COLOR_TEXT}; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        header {{ background: {COLOR_PRIMARY}; color: white; padding: 30px 20px; text-align: center; margin-bottom: 30px; }}
        header h1 {{ font-size: 2em; margin-bottom: 10px; }}
        header p {{ font-size: 1.1em; opacity: 0.95; }}
        .search-box {{ margin: 20px 0; }}
        #searchBox {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 1em; }}
        .jobs-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }}
        .job-card {{ background: white; border-left: 4px solid {COLOR_PRIMARY}; padding: 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .job-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }}
        .job-header {{ display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px; gap: 10px; }}
        .job-header h3 {{ flex: 1; color: {COLOR_PRIMARY}; font-size: 1.2em; }}
        .sector {{ font-size: 0.75em; padding: 4px 8px; border-radius: 3px; background: {COLOR_PRIMARY}; color: white; white-space: nowrap; }}
        .job-meta {{ display: flex; gap: 12px; margin: 12px 0; font-size: 0.9em; flex-wrap: wrap; }}
        .contract {{ color: #3498db; }}
        .city {{ color: #666; }}
        .job-details {{ display: flex; gap: 12px; margin-top: 12px; font-size: 0.85em; flex-wrap: wrap; }}
        .salary {{ color: #27ae60; font-weight: bold; }}
        .posted {{ color: #999; }}
        .count {{ color: #666; font-size: 0.95em; margin: 20px 0; }}
        footer {{ text-align: center; margin-top: 40px; padding: 20px; color: #999; font-size: 0.9em; }}
        a {{ color: {COLOR_PRIMARY}; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <header>
        <h1>JobsInRomania</h1>
        <p>Daily job opportunities for workers in Romania</p>
    </header>
    <div class="container">
        <div class="search-box">
            <input type="text" id="searchBox" placeholder="Search by job title, city, or sector...">
        </div>
        <p class="count"><strong id="jobCount">{len(jobs)}</strong> jobs available</p>
        <div class="jobs-grid" id="jobsGrid">
"""

    for job in jobs:
        html += format_job_card(job)

    html += """        </div>
        <footer>
            <p>Updated daily. Source: ANOFM. &copy; 2026 JobsInRomania.</p>
        </footer>
    </div>

    <script>
    const allCards = document.querySelectorAll('.job-card');
    const searchBox = document.getElementById('searchBox');
    const jobCount = document.getElementById('jobCount');

    searchBox.addEventListener('keyup', function(e) {
        const query = e.target.value.toLowerCase();
        let visibleCount = 0;
        allCards.forEach(card => {
            const text = card.textContent.toLowerCase();
            const isVisible = text.includes(query);
            card.classList.toggle('hidden', !isVisible);
            if (isVisible) visibleCount++;
        });
        jobCount.textContent = visibleCount;
    });
    </script>
</body>
</html>
"""

    os.makedirs(PAGES_DIR, exist_ok=True)
    with open(os.path.join(PAGES_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    jobs = load_jobs()
    if not jobs:
        print("No jobs found in data/jobs.json")
        return

    build_index(jobs)
    print(f"Generated index.html for {len(jobs)} jobs")


if __name__ == "__main__":
    main()
