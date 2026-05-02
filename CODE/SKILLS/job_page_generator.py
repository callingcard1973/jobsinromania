#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
job_page_generator.py - Generate lead-capture job listing pages

Reusable skill for generating job listing pages with:
- Formspree form integration
- WhatsApp CTA
- Country filters
- Empty state handling
- SEO meta tags
- Schema.org JobPosting structured data

Usage:
    # Generate for a domain
    python3 /opt/ACTIVE/INFRA/SKILLS/job_page_generator.py \\
        --domain aluminumrecyclehub.com \\
        --jobs /opt/ACTIVE/OPENDATA/DATA/RECYCLING/jobs.json \\
        --output /opt/ACTIVE/WEB/WEBSITES/output/ \\
        --email partners@aluminumrecyclehub.com \\
        --whatsapp 40722789938 \\
        --name "Tudor Seicarescu"

    # Use config file
    python3 /opt/ACTIVE/INFRA/SKILLS/job_page_generator.py --config /path/to/config.json

    # Preview without writing
    python3 /opt/ACTIVE/INFRA/SKILLS/job_page_generator.py ... --dry-run
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii


@dataclass
class SiteConfig:
    """Configuration for job page generation."""
    domain: str
    jobs_path: str
    output_dir: str
    form_email: str
    whatsapp: str = ""
    whatsapp_display: str = ""
    contact_name: str = ""
    contact_email: str = ""
    site_name: str = ""
    site_emoji: str = ""
    form_subject: str = ""
    primary_color: str = "#1b5e20"
    accent_color: str = "#4caf50"
    countries: List[str] = field(default_factory=lambda: [
        'Germany', 'Netherlands', 'Belgium', 'Austria',
        'Sweden', 'Denmark', 'Poland', 'Czech Republic'
    ])
    positions: List[str] = field(default_factory=lambda: [
        'Production Worker', 'Machine Operator', 'Warehouse Worker',
        'Forklift Driver', 'Quality Control', 'Driver/Logistics'
    ])
    industry: str = "Industry"

    def __post_init__(self):
        if not self.whatsapp_display and self.whatsapp:
            # Format: 40722789938 -> +40 722 789 938
            w = self.whatsapp
            if len(w) >= 10:
                self.whatsapp_display = f"+{w[:2]} {w[2:5]} {w[5:8]} {w[8:]}"
        if not self.contact_email:
            self.contact_email = self.form_email
        if not self.site_name:
            self.site_name = self.domain.replace('.', ' ').title()
        if not self.form_subject:
            self.form_subject = f"Job Application - {self.domain}"


class JobPageGenerator:
    """Generate job listing pages with lead capture forms."""

    def __init__(self, config: SiteConfig):
        self.config = config
        self.jobs = []

    def load_jobs(self) -> List[dict]:
        """Load jobs from JSON file."""
        jobs_path = Path(self.config.jobs_path)
        if not jobs_path.exists():
            print(f"No jobs file found at {jobs_path} - generating empty pages")
            self.jobs = []
            return []

        with open(jobs_path) as f:
            data = json.load(f)

        # Handle both {jobs: [...]} and direct array
        if isinstance(data, list):
            self.jobs = data
        else:
            self.jobs = data.get('jobs', [])

        print(f"Loaded {len(self.jobs)} jobs")
        return self.jobs

    def _generate_country_options(self) -> str:
        return '\n'.join(f'<option value="{c}">{c}</option>' for c in self.config.countries)

    def _generate_position_options(self) -> str:
        return '\n'.join(f'<option value="{p}">{p}</option>' for p in self.config.positions)

    def _generate_country_filters(self, current_country: str = None) -> str:
        countries = defaultdict(int)
        for job in self.jobs:
            country = job.get('country', 'Unknown')
            countries[country] += 1

        filters = ['<a href="jobs.html"' + (' class="active"' if not current_country else '') + '>All</a>']
        for country, count in sorted(countries.items()):
            if country == 'Unknown':
                continue
            code = country.lower()[:2] if country != 'Czech Republic' else 'cz'
            active = ' class="active"' if current_country == country else ''
            filters.append(f'<a href="{code}.html"{active}>{country} ({count})</a>')

        return '\n            '.join(filters)

    def _generate_jobs_json(self) -> str:
        safe_jobs = []
        for job in self.jobs:
            safe_jobs.append({
                'url': job.get('url', '#'),
                'title': to_ascii(job.get('title', 'Position')),
                'company': to_ascii(job.get('company', 'Company')),
                'location': to_ascii(job.get('location', '')),
                'country': job.get('country', 'Europe'),
                'email': job.get('email', ''),
                'phone': job.get('phone', ''),
                'scraped_date': job.get('scraped_date', '')
            })
        return json.dumps(safe_jobs)

    def _generate_schema_jobs(self) -> str:
        schema_items = []
        for i, job in enumerate(self.jobs[:20], 1):
            schema_items.append({
                "@type": "ListItem",
                "position": i,
                "item": {
                    "@type": "JobPosting",
                    "title": job.get('title', 'Position'),
                    "hiringOrganization": {"@type": "Organization", "name": job.get('company', 'Company')},
                    "jobLocation": {"@type": "Place", "address": job.get('country', 'Europe')},
                    "url": job.get('url', '')
                }
            })
        return json.dumps(schema_items)

    def _generate_job_html(self, job: dict) -> str:
        buttons = ['<a href="#apply" class="btn btn-primary">Apply Now</a>']
        if job.get('email'):
            buttons.append(f'<a href="mailto:{job["email"]}" class="btn btn-secondary">Email</a>')
        buttons.append(f'<a href="{job.get("url", "#")}" target="_blank" class="btn btn-secondary">View</a>')

        return f'''
<div class="job-card">
    <h3 class="job-title"><a href="{job.get('url', '#')}" target="_blank">{to_ascii(job.get('title', 'Position'))}</a></h3>
    <div class="job-company">{to_ascii(job.get('company', 'Company'))}</div>
    <div class="job-meta">
        <span>📍 {to_ascii(job.get('location', ''))}</span>
        <span>🌍 {job.get('country', 'Europe')}</span>
    </div>
    <div class="job-details">
        <div>{self.config.site_emoji} {self.config.industry}</div>
        <div>⏰ Full-time</div>
    </div>
    <div class="job-footer">
        <span class="job-date">Posted: {job.get('scraped_date', 'Recently')}</span>
        <div class="btn-group">
            {chr(10).join(buttons)}
        </div>
    </div>
</div>
'''

    def _generate_jobs_html(self) -> str:
        return '\n'.join(self._generate_job_html(job) for job in self.jobs)

    def _generate_empty_state(self) -> str:
        if self.jobs:
            return ''
        return f'''
<div class="empty-state">
    <h2>No Jobs Currently Listed</h2>
    <p>We're actively sourcing new opportunities.</p>
    <p>Register below and we'll notify you when positions open up!</p>
    <div style="margin-top: 20px;">
        <a href="https://wa.me/{self.config.whatsapp}" class="btn btn-whatsapp btn-large">WhatsApp Us: {self.config.whatsapp_display}</a>
    </div>
</div>
'''

    def generate_jobs_page(self, country: str = None, filename: str = 'jobs.html') -> str:
        """Generate main jobs.html or country page."""
        jobs = self.jobs if not country else [j for j in self.jobs if j.get('country') == country]
        companies = set(j.get('company') for j in jobs if j.get('company'))
        countries = set(j.get('country') for j in jobs if j.get('country'))

        title = f"Jobs in {country}" if country else f"{self.config.industry} Jobs in Europe"
        description = f"Find {self.config.industry.lower()} jobs in {'Europe' if not country else country}."
        header_title = f"{self.config.site_emoji} {title}"
        header_subtitle = f"{len(jobs)} open positions" if jobs else "Register for future opportunities"

        c = self.config
        return self._get_main_template().format(
            title=title,
            description=description,
            keywords=', '.join(sorted(countries)) if countries else 'Germany, Netherlands, Belgium',
            canonical_url=f'https://{c.domain}/jobs/{filename}',
            header_title=header_title,
            header_subtitle=header_subtitle,
            job_count=len(jobs),
            country_count=len(countries) if countries else len(c.countries),
            company_count=len(companies),
            country_filters=self._generate_country_filters(country),
            jobs_html=self._generate_jobs_html() if not country else '\n'.join(self._generate_job_html(j) for j in jobs),
            jobs_json=self._generate_jobs_json() if not country else json.dumps([]),
            empty_state=self._generate_empty_state() if not country else '',
            schema_jobs=self._generate_schema_jobs(),
            country_options=self._generate_country_options(),
            position_options=self._generate_position_options(),
            formspree_email=c.form_email,
            form_subject=c.form_subject,
            domain=c.domain,
            site_name=c.site_name,
            site_emoji=c.site_emoji,
            whatsapp=c.whatsapp,
            whatsapp_display=c.whatsapp_display,
            contact_name=c.contact_name,
            contact_email=c.contact_email,
            primary_color=c.primary_color,
            accent_color=c.accent_color,
            updated=datetime.now().strftime('%Y-%m-%d %H:%M'),
            year=datetime.now().year
        )

    def generate_apply_page(self) -> str:
        """Generate standalone apply.html page."""
        c = self.config
        return self._get_apply_template().format(
            formspree_email=c.form_email,
            form_subject=c.form_subject,
            domain=c.domain,
            site_name=c.site_name,
            site_emoji=c.site_emoji,
            whatsapp=c.whatsapp,
            whatsapp_display=c.whatsapp_display,
            contact_name=c.contact_name,
            country_options=self._generate_country_options(),
            position_options=self._generate_position_options(),
            primary_color=c.primary_color,
            accent_color=c.accent_color
        )

    def generate_all(self, dry_run: bool = False):
        """Generate all pages and save to output directory."""
        self.load_jobs()
        output_dir = Path(self.config.output_dir)

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        pages = {}

        # Main jobs page
        pages['jobs.html'] = self.generate_jobs_page()
        print(f"{'Would generate' if dry_run else 'Generated'}: jobs.html")

        # Apply page
        pages['apply.html'] = self.generate_apply_page()
        print(f"{'Would generate' if dry_run else 'Generated'}: apply.html")

        # Country pages
        by_country = defaultdict(list)
        for job in self.jobs:
            country = job.get('country', 'Unknown')
            by_country[country].append(job)

        for country in by_country:
            if country == 'Unknown':
                continue
            code = country.lower()[:2] if country != 'Czech Republic' else 'cz'
            filename = f'{code}.html'
            pages[filename] = self.generate_jobs_page(country=country, filename=filename)
            print(f"{'Would generate' if dry_run else 'Generated'}: {filename}")

        # Index redirect
        pages['index.html'] = '''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=jobs.html">
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to <a href="jobs.html">jobs listing</a>...</p>
</body>
</html>
'''
        print(f"{'Would generate' if dry_run else 'Generated'}: index.html")

        if not dry_run:
            for filename, content in pages.items():
                (output_dir / filename).write_text(content, encoding='utf-8')

        print(f"\nDone! {'Would generate' if dry_run else 'Generated'} {len(pages)} pages in {output_dir}")
        return pages

    def _get_main_template(self) -> str:
        """Return the main jobs page HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {site_name}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <link rel="canonical" href="{canonical_url}">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>{site_emoji}</text></svg>">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"ItemList","name":"{title}","numberOfItems":{job_count},"itemListElement":{schema_jobs}}}</script>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        :root{{--primary:{primary_color};--accent:{accent_color};--light:#f5f5f5;--dark:#1a1a1a;--border:#e0e0e0}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.6;color:var(--dark);background:var(--light)}}
        header{{background:var(--primary);color:#fff;padding:12px 0;position:sticky;top:0;z-index:100}}
        .header-content{{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
        .logo{{font-size:1.2rem;font-weight:bold;text-decoration:none;color:#fff}}
        nav a{{color:#fff;text-decoration:none;margin-left:15px;font-size:0.9rem}}
        nav a:hover{{color:var(--accent)}}
        .hero{{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;padding:30px 20px;text-align:center}}
        .hero h1{{font-size:1.8rem;margin-bottom:8px}}
        .stats{{display:flex;gap:15px;justify-content:center;margin:20px 0;flex-wrap:wrap}}
        .stat{{background:rgba(255,255,255,0.15);padding:12px 20px;border-radius:8px;text-align:center}}
        .stat-num{{font-size:1.8rem;font-weight:bold}}
        .stat-label{{font-size:0.85rem;opacity:0.9}}
        .filters{{background:#fff;padding:15px;max-width:1200px;margin:-15px auto 20px;border-radius:8px;box-shadow:0 3px 10px rgba(0,0,0,0.1);display:flex;gap:12px;flex-wrap:wrap}}
        .filters input{{padding:10px 15px;border:2px solid var(--border);border-radius:6px;flex:1;min-width:200px}}
        .filters select{{padding:10px 15px;border:2px solid var(--border);border-radius:6px;min-width:150px}}
        .main-content{{max-width:1200px;margin:0 auto;padding:0 15px 30px}}
        .country-pills{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
        .country-pills a{{padding:6px 14px;background:var(--light);color:var(--primary);border-radius:20px;text-decoration:none;font-size:0.85rem;border:1px solid var(--border)}}
        .country-pills a:hover,.country-pills a.active{{background:var(--primary);color:#fff}}
        .results-info{{margin-bottom:15px;color:#666;font-size:0.9rem}}
        .jobs-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:15px}}
        .job-card{{background:#fff;border-radius:8px;padding:18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);border-left:4px solid var(--accent)}}
        .job-card:hover{{transform:translateY(-3px);box-shadow:0 6px 15px rgba(0,0,0,0.12)}}
        .job-title{{font-size:1.05rem;color:var(--primary);margin-bottom:6px;font-weight:600}}
        .job-title a{{color:inherit;text-decoration:none}}
        .job-company{{font-weight:600;color:#444;margin-bottom:8px}}
        .job-meta{{display:flex;gap:12px;flex-wrap:wrap;color:#666;font-size:0.85rem;margin-bottom:12px}}
        .job-details{{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:10px;background:var(--light);border-radius:6px;font-size:0.85rem;margin-bottom:12px}}
        .job-footer{{display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid var(--border);gap:8px;flex-wrap:wrap}}
        .job-date{{color:#999;font-size:0.8rem}}
        .btn-group{{display:flex;gap:6px;flex-wrap:wrap}}
        .btn{{padding:7px 14px;border-radius:5px;font-size:0.85rem;font-weight:500;text-decoration:none;cursor:pointer;border:none}}
        .btn-primary{{background:var(--accent);color:#fff}}
        .btn-primary:hover{{opacity:0.9}}
        .btn-secondary{{background:#e8e8e8;color:var(--primary)}}
        .btn-whatsapp{{background:#25d366;color:#fff}}
        .btn-large{{padding:12px 24px;font-size:1rem}}
        .apply-section{{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);padding:30px;border-radius:12px;margin-top:30px;border:2px solid var(--accent)}}
        .apply-section h3{{color:var(--primary);margin-bottom:10px;text-align:center;font-size:1.4rem}}
        .apply-section>p{{text-align:center;color:#555;margin-bottom:25px}}
        .apply-form{{max-width:600px;margin:0 auto;background:#fff;padding:25px;border-radius:10px}}
        .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}
        .form-group{{margin-bottom:18px}}
        .form-group label{{display:block;margin-bottom:6px;font-weight:600;color:var(--primary)}}
        .form-group input,.form-group select,.form-group textarea{{width:100%;padding:11px 14px;border:2px solid var(--border);border-radius:6px}}
        .required{{color:#d32f2f}}
        .form-submit{{text-align:center;margin-top:20px}}
        .form-submit .btn{{width:100%;padding:14px;font-size:1.1rem}}
        .empty-state{{text-align:center;padding:50px 20px;background:#fff;border-radius:12px;margin:20px 0}}
        .empty-state h2{{color:var(--primary);margin-bottom:15px}}
        .contact-box{{background:#fff;padding:25px;border-radius:10px;margin-top:25px;text-align:center;border:1px solid var(--border)}}
        .contact-box h4{{color:var(--primary);margin-bottom:10px}}
        .contact-btns{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:15px}}
        footer{{background:var(--primary);color:#fff;padding:25px 20px;text-align:center;margin-top:40px}}
        footer a{{color:var(--accent)}}
        .updated{{font-size:0.85rem;color:#888;margin-top:20px;text-align:center}}
        @media(max-width:600px){{.hero h1{{font-size:1.4rem}}.filters{{flex-direction:column}}.jobs-grid{{grid-template-columns:1fr}}.form-row{{grid-template-columns:1fr}}}}
    </style>
</head>
<body>
    <header><div class="header-content">
        <a href="/" class="logo">{site_emoji} {site_name}</a>
        <nav><a href="/">Home</a><a href="/jobs/">Jobs</a><a href="/jobs/apply.html">Apply</a></nav>
    </div></header>

    <div class="hero">
        <h1>{header_title}</h1>
        <p>{header_subtitle}</p>
        <div class="stats">
            <div class="stat"><div class="stat-num">{job_count}</div><div class="stat-label">Positions</div></div>
            <div class="stat"><div class="stat-num">{country_count}</div><div class="stat-label">Countries</div></div>
            <div class="stat"><div class="stat-num">{company_count}</div><div class="stat-label">Companies</div></div>
        </div>
    </div>

    <div class="filters">
        <input type="text" id="search" placeholder="Search jobs...">
        <select id="sort"><option value="newest">Newest</option><option value="company">Company</option><option value="country">Country</option></select>
    </div>

    <div class="main-content">
        <div class="country-pills">{country_filters}</div>
        <p class="results-info">Showing <span id="showing">{job_count}</span> jobs</p>
        {empty_state}
        <div class="jobs-grid" id="jobs-container">{jobs_html}</div>
        <p class="updated">Updated: {updated}</p>

        <div class="apply-section" id="apply">
            <h3>Apply for Jobs</h3>
            <p>Register your interest and we'll match you with opportunities</p>
            <form action="https://formspree.io/f/{formspree_email}" method="POST" class="apply-form">
                <input type="hidden" name="_subject" value="{form_subject}">
                <div class="form-row">
                    <div class="form-group"><label>Full Name <span class="required">*</span></label><input type="text" name="name" required></div>
                    <div class="form-group"><label>Email <span class="required">*</span></label><input type="email" name="email" required></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Phone <span class="required">*</span></label><input type="tel" name="phone" required></div>
                    <div class="form-group"><label>Target Country</label><select name="target_country"><option value="">Select...</option>{country_options}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Position</label><select name="position"><option value="">Any</option>{position_options}</select></div>
                    <div class="form-group"><label>Experience</label><select name="experience"><option value="0-1">0-1 years</option><option value="1-3">1-3</option><option value="3-5">3-5</option><option value="5+">5+</option></select></div>
                </div>
                <div class="form-group"><label>Message</label><textarea name="message" rows="3"></textarea></div>
                <div class="form-submit"><button type="submit" class="btn btn-primary btn-large">Submit Application</button></div>
            </form>
            <div class="contact-box">
                <h4>Direct Contact</h4>
                <p><strong>{contact_name}</strong></p>
                <div class="contact-btns">
                    <a href="https://wa.me/{whatsapp}" class="btn btn-whatsapp">WhatsApp: {whatsapp_display}</a>
                    <a href="mailto:{contact_email}" class="btn btn-primary">Email</a>
                </div>
            </div>
        </div>
    </div>

    <footer>
        <p>{site_emoji} <a href="/">{site_name}</a></p>
        <p style="margin-top:10px"><strong>{contact_name}</strong> | <a href="https://wa.me/{whatsapp}">{whatsapp_display}</a> | <a href="mailto:{contact_email}">{contact_email}</a></p>
        <p style="margin-top:15px;font-size:0.8rem;opacity:0.7">&copy; {year} {site_name}</p>
    </footer>

    <script>
    const allJobs = {jobs_json};
    function renderJobs(jobs) {{
        const c = document.getElementById('jobs-container');
        document.getElementById('showing').textContent = jobs.length;
        if (!jobs.length) {{ c.innerHTML = ''; return; }}
        c.innerHTML = jobs.map(j => `
            <div class="job-card">
                <h3 class="job-title"><a href="${{j.url}}">${{j.title}}</a></h3>
                <div class="job-company">${{j.company}}</div>
                <div class="job-meta"><span>📍 ${{j.location||j.country}}</span><span>🌍 ${{j.country}}</span></div>
                <div class="job-footer">
                    <span class="job-date">${{j.scraped_date||'Recently'}}</span>
                    <div class="btn-group"><a href="#apply" class="btn btn-primary">Apply</a><a href="${{j.url}}" class="btn btn-secondary">View</a></div>
                </div>
            </div>
        `).join('');
    }}
    function filterJobs() {{
        const s = document.getElementById('search').value.toLowerCase();
        const sort = document.getElementById('sort').value;
        let f = allJobs.filter(j => !s || `${{j.title}} ${{j.company}} ${{j.country}}`.toLowerCase().includes(s));
        if (sort==='company') f.sort((a,b)=>(a.company||'').localeCompare(b.company||''));
        if (sort==='country') f.sort((a,b)=>(a.country||'').localeCompare(b.country||''));
        renderJobs(f);
    }}
    document.getElementById('search').addEventListener('input', filterJobs);
    document.getElementById('sort').addEventListener('change', filterJobs);
    renderJobs(allJobs);
    </script>
</body>
</html>'''

    def _get_apply_template(self) -> str:
        """Return the apply page HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apply Now - {site_name}</title>
    <meta name="description" content="Apply for jobs. Submit your application today.">
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>{site_emoji}</text></svg>">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;min-height:100vh}}
        .header{{background:linear-gradient(135deg,{primary_color},{accent_color});color:white;padding:20px;text-align:center}}
        .header h1{{font-size:1.8rem;margin-bottom:5px}}
        .container{{max-width:600px;margin:30px auto;padding:0 20px}}
        .form-card{{background:white;border-radius:15px;padding:30px;box-shadow:0 5px 20px rgba(0,0,0,0.1)}}
        .form-group{{margin-bottom:20px}}
        .form-row{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}
        label{{display:block;margin-bottom:8px;font-weight:600;color:{primary_color}}}
        input,select,textarea{{width:100%;padding:12px 15px;border:2px solid #e0e0e0;border-radius:8px;font-size:1rem}}
        input:focus,select:focus,textarea:focus{{outline:none;border-color:{accent_color}}}
        .btn{{width:100%;padding:15px;background:{accent_color};color:white;border:none;border-radius:8px;font-size:1.1rem;font-weight:600;cursor:pointer}}
        .btn:hover{{opacity:0.9}}
        .btn-whatsapp{{background:#25d366;margin-top:15px}}
        .back-link{{text-align:center;margin-top:20px}}
        .back-link a{{color:{primary_color};text-decoration:none;font-weight:500}}
        .required{{color:#d32f2f}}
        .contact-box{{background:#f5f5f5;border-radius:10px;padding:20px;margin-top:25px;text-align:center}}
        .contact-box h3{{color:{primary_color};margin-bottom:10px}}
        @media(max-width:600px){{.form-row{{grid-template-columns:1fr}}}}
    </style>
</head>
<body>
    <div class="header"><h1>{site_emoji} Apply for Jobs</h1><p>Submit your application</p></div>
    <div class="container">
        <div class="form-card">
            <form action="https://formspree.io/f/{formspree_email}" method="POST">
                <input type="hidden" name="_subject" value="{form_subject}">
                <div class="form-row">
                    <div class="form-group"><label>Full Name <span class="required">*</span></label><input type="text" name="name" required></div>
                    <div class="form-group"><label>Email <span class="required">*</span></label><input type="email" name="email" required></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Phone <span class="required">*</span></label><input type="tel" name="phone" required></div>
                    <div class="form-group"><label>Country of Origin</label><select name="origin_country"><option value="">Select...</option><option>Romania</option><option>Moldova</option><option>Ukraine</option><option>Nepal</option><option>India</option><option>Other</option></select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Target Country <span class="required">*</span></label><select name="target_country" required><option value="">Where to work?</option>{country_options}</select></div>
                    <div class="form-group"><label>Position</label><select name="position"><option value="">Any</option>{position_options}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Experience</label><select name="experience"><option value="0-1">0-1 years</option><option value="1-3">1-3</option><option value="3-5">3-5</option><option value="5+">5+</option></select></div>
                    <div class="form-group"><label>Available From</label><input type="date" name="available_from"></div>
                </div>
                <div class="form-group"><label>Passport?</label><select name="passport"><option value="yes">Yes</option><option value="no">No, but can get</option></select></div>
                <div class="form-group"><label>Message</label><textarea name="message" rows="4"></textarea></div>
                <button type="submit" class="btn">Submit Application</button>
            </form>
            <div class="contact-box">
                <h3>Prefer WhatsApp?</h3>
                <p><strong>{contact_name}</strong></p>
                <a href="https://wa.me/{whatsapp}" class="btn btn-whatsapp">WhatsApp: {whatsapp_display}</a>
            </div>
        </div>
        <div class="back-link"><a href="jobs.html">Back to Jobs</a></div>
    </div>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(
        description='Generate job listing pages with lead capture forms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Generate for a domain
  python3 job_page_generator.py --domain example.com --jobs jobs.json \\
      --output ./output --email jobs@example.com --whatsapp 40722789938

  # Use config file
  python3 job_page_generator.py --config config.json

  # Preview only
  python3 job_page_generator.py --domain example.com --jobs jobs.json \\
      --output ./output --email jobs@example.com --dry-run
'''
    )

    parser.add_argument('--domain', help='Domain name (e.g., example.com)')
    parser.add_argument('--jobs', help='Path to jobs.json file')
    parser.add_argument('--output', help='Output directory for generated pages')
    parser.add_argument('--email', default='manpowerdristor@gmail.com', help='Form submission email (Formspree)')
    parser.add_argument('--whatsapp', default='40722789938', help='WhatsApp number (no +)')
    parser.add_argument('--name', default='Tudor Seicarescu', help='Contact person name')
    parser.add_argument('--emoji', default='💼', help='Site emoji')
    parser.add_argument('--industry', default='Industry', help='Industry name')
    parser.add_argument('--config', help='JSON config file (overrides other args)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')

    args = parser.parse_args()

    # Load config from file or args
    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        config = SiteConfig(**cfg)
    else:
        if not all([args.domain, args.jobs, args.output]):
            parser.error("Required: --domain, --jobs, --output (or use --config)")

        config = SiteConfig(
            domain=args.domain,
            jobs_path=args.jobs,
            output_dir=args.output,
            form_email=args.email,
            whatsapp=args.whatsapp,
            contact_name=args.name,
            site_emoji=args.emoji,
            industry=args.industry
        )

    generator = JobPageGenerator(config)
    generator.generate_all(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
