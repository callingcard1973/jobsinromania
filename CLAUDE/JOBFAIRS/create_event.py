#!/usr/bin/env python3
"""
Job Fair Event Creator — generates all materials for a specific job fair event.

Usage:
    python create_event.py --county "Arges" --date "2025-04-15" --venue "Casa Sindicatelor Pitesti" --employers 50
    python create_event.py --county "Arges" --date "2025-04-15" --venue "Test" --list    # list existing events
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
EVENTS_DIR = SCRIPT_DIR / "events"
JOBFAIR_DIR = SCRIPT_DIR / "jobfair"
REGISTRATION_URL = "https://interjob.ro/jobfair/employer.html"
WORKER_URL = "https://interjob.ro/jobfair/worker.html"

# Romanian county names for display
COUNTIES = {
    "AB": "Alba", "AR": "Arad", "AG": "Arges", "BC": "Bacau", "BH": "Bihor",
    "BN": "Bistrita-Nasaud", "BT": "Botosani", "BV": "Brasov", "BR": "Braila",
    "B": "Bucuresti", "BZ": "Buzau", "CS": "Caras-Severin", "CL": "Calarasi",
    "CJ": "Cluj", "CT": "Constanta", "CV": "Covasna", "DB": "Dambovita",
    "DJ": "Dolj", "GL": "Galati", "GR": "Giurgiu", "GJ": "Gorj",
    "HR": "Harghita", "HD": "Hunedoara", "IL": "Ialomita", "IS": "Iasi",
    "IF": "Ilfov", "MM": "Maramures", "MH": "Mehedinti", "MS": "Mures",
    "NT": "Neamt", "OT": "Olt", "PH": "Prahova", "SM": "Satu Mare",
    "SJ": "Salaj", "SB": "Sibiu", "SV": "Suceava", "TR": "Teleorman",
    "TM": "Timis", "TL": "Tulcea", "VS": "Vaslui", "VL": "Valcea", "VN": "Vrancea",
}


def slugify(text):
    """Convert text to a URL/directory-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def format_date_ro(date_str):
    """Format YYYY-MM-DD to Romanian-style date."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    months_ro = {1: 'Ianuarie', 2: 'Februarie', 3: 'Martie', 4: 'Aprilie',
                 5: 'Mai', 6: 'Iunie', 7: 'Iulie', 8: 'August',
                 9: 'Septembrie', 10: 'Octombrie', 11: 'Noiembrie', 12: 'Decembrie'}
    return f"{dt.day} {months_ro[dt.month]} {dt.year}"


def format_date_en(date_str):
    """Format YYYY-MM-DD to English-style date."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%B %d, %Y')


def generate_poster(county, date_str, venue, employers, lang='ro'):
    """Generate printable A4 poster HTML."""
    if lang == 'ro':
        title = "TARG INTERNATIONAL DE LOCURI DE MUNCA"
        subtitle = f"Judetul {county}"
        date_display = format_date_ro(date_str)
        venue_label = "Locatie"
        employers_label = "Angajatori participanti"
        sectors_label = "Sectoare"
        free_label = "INTRARE LIBERA"
        bring_label = "Aduceti CV-ul!"
        info_label = "Informatii"
        organized_by = "Organizat de InterJob Solutions in parteneriat cu EURES si ANOFM"
    else:
        title = "INTERNATIONAL JOB FAIR"
        subtitle = f"{county} County, Romania"
        date_display = format_date_en(date_str)
        venue_label = "Venue"
        employers_label = "Participating employers"
        sectors_label = "Sectors"
        free_label = "FREE ENTRY"
        bring_label = "Bring your CV!"
        info_label = "Information"
        organized_by = "Organized by InterJob Solutions in partnership with EURES and ANOFM"

    sectors = ["Factory", "Construction", "Warehouse", "Care", "HoReCa",
               "Agriculture", "Electrical", "Mechanics", "Meat", "Transport", "IT"]

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <title>{title} - {county}</title>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, Helvetica, sans-serif; background: white; color: #333; }}
        .poster {{
            width: 210mm; min-height: 297mm; margin: 0 auto; padding: 20mm;
            border: 3px solid #065f46; position: relative;
        }}
        .poster-header {{
            background: linear-gradient(135deg, #065f46, #10b981);
            color: white; text-align: center; padding: 25px; margin: -20mm -20mm 20px;
            border-bottom: 5px solid #065f46;
        }}
        .poster-header h1 {{ font-size: 32px; letter-spacing: 2px; margin-bottom: 10px; }}
        .poster-header h2 {{ font-size: 22px; font-weight: normal; opacity: 0.9; }}
        .poster-date {{
            text-align: center; font-size: 28px; font-weight: bold; color: #065f46;
            padding: 20px; margin: 20px 0; border: 2px solid #065f46; border-radius: 8px;
            background: #f0fdf4;
        }}
        .poster-venue {{ text-align: center; font-size: 18px; margin: 15px 0; }}
        .poster-venue strong {{ color: #065f46; }}
        .poster-stats {{
            display: flex; justify-content: center; gap: 30px; margin: 25px 0;
            text-align: center;
        }}
        .poster-stat {{ padding: 15px; }}
        .poster-stat .num {{ font-size: 36px; font-weight: bold; color: #065f46; }}
        .poster-stat .lbl {{ font-size: 14px; color: #666; }}
        .poster-sectors {{
            display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 20px 0;
        }}
        .poster-sectors span {{
            background: #f0fdf4; border: 1px solid #10b981; padding: 6px 14px;
            border-radius: 20px; font-size: 13px; color: #065f46;
        }}
        .poster-free {{
            text-align: center; font-size: 26px; font-weight: bold; color: white;
            background: #065f46; padding: 15px; margin: 20px 0; border-radius: 8px;
        }}
        .poster-free small {{ display: block; font-size: 16px; font-weight: normal; opacity: 0.9; }}
        .poster-footer {{
            text-align: center; margin-top: 20px; padding-top: 15px;
            border-top: 2px solid #eee; font-size: 14px; color: #666;
        }}
        .poster-footer a {{ color: #065f46; }}
        @media print {{
            body {{ background: white; }}
            .poster {{ border: none; }}
        }}
    </style>
</head>
<body>
    <div class="poster">
        <div class="poster-header">
            <h1>{title}</h1>
            <h2>{subtitle}</h2>
        </div>

        <div class="poster-date">{date_display}</div>

        <div class="poster-venue">
            <strong>{venue_label}:</strong> {venue}
        </div>

        <div class="poster-stats">
            <div class="poster-stat">
                <div class="num">{employers}+</div>
                <div class="lbl">{employers_label}</div>
            </div>
            <div class="poster-stat">
                <div class="num">15+</div>
                <div class="lbl">{"Tari" if lang == "ro" else "Countries"}</div>
            </div>
        </div>

        <p style="text-align:center; font-weight:bold; color:#065f46; margin:15px 0;">
            {sectors_label}:
        </p>
        <div class="poster-sectors">
            {"".join(f'<span>{s}</span>' for s in sectors)}
        </div>

        <div class="poster-free">
            {free_label}
            <small>{bring_label}</small>
        </div>

        <div class="poster-footer">
            <p><strong>{info_label}:</strong> office@interjob.ro | interjob.ro/jobfair</p>
            <p style="margin-top:8px; font-size:12px;">{organized_by}</p>
        </div>
    </div>
</body>
</html>"""


def generate_badges(county, date_str, venue):
    """Generate printable badge templates (8 per A4 page — 4 employer, 4 worker)."""
    date_ro = format_date_ro(date_str)

    badge_css = """
        @page { size: A4; margin: 10mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; }
        .badges { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .badge {
            border: 2px solid #065f46; border-radius: 8px; padding: 15px;
            height: 130mm; width: 90mm; text-align: center;
            display: flex; flex-direction: column; justify-content: space-between;
            page-break-inside: avoid;
        }
        .badge-type {
            background: #065f46; color: white; padding: 8px; border-radius: 4px;
            font-size: 14px; font-weight: bold; text-transform: uppercase;
        }
        .badge-type.worker { background: #10b981; }
        .badge-name {
            font-size: 24px; font-weight: bold; color: #333; padding: 15px 0;
            border-bottom: 1px dashed #ccc;
            min-height: 60px;
        }
        .badge-company { font-size: 16px; color: #666; padding: 10px 0; }
        .badge-event { font-size: 12px; color: #999; }
        .badge-name-line { border-bottom: 1px solid #ccc; min-height: 30px; margin: 5px 10px; }
        @media print { .no-print { display: none; } }
    """

    badges_html = ""
    for i in range(4):
        badges_html += f"""
        <div class="badge">
            <div class="badge-type">ANGAJATOR / EMPLOYER</div>
            <div class="badge-name"><div class="badge-name-line"></div></div>
            <div class="badge-company"><div class="badge-name-line"></div></div>
            <div class="badge-event">Targ de Locuri de Munca — {county} — {date_ro}</div>
        </div>"""

    for i in range(4):
        badges_html += f"""
        <div class="badge">
            <div class="badge-type worker">PARTICIPANT / WORKER</div>
            <div class="badge-name"><div class="badge-name-line"></div></div>
            <div class="badge-company"><div class="badge-name-line"></div></div>
            <div class="badge-event">Targ de Locuri de Munca — {county} — {date_ro}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Badges - {county} - {date_str}</title>
    <style>{badge_css}</style>
</head>
<body>
    <p class="no-print" style="text-align:center; padding:10px; color:#666;">
        Print this page to create badges. Fill in names by hand or customize before printing.
    </p>
    <div class="badges">{badges_html}
    </div>
</body>
</html>"""


def generate_employer_list(county, date_str):
    """Generate empty employer directory template."""
    date_ro = format_date_ro(date_str)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Employer Directory - {county} Job Fair - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #065f46, #10b981);
            color: white; text-align: center; padding: 25px; border-radius: 8px 8px 0 0;
        }}
        .header h1 {{ font-size: 1.6em; }}
        .header p {{ opacity: 0.9; margin-top: 5px; }}
        .content {{
            background: white; padding: 25px; border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #065f46; color: white; padding: 10px; text-align: left; font-size: 0.9em; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 0.9em; }}
        tr:hover {{ background: #f0fdf4; }}
        .note {{
            background: #ecfdf5; border: 1px solid #10b981; padding: 15px;
            border-radius: 6px; margin: 15px 0; font-size: 14px;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Employer Directory / Director Angajatori</h1>
            <p>{county} — {date_ro}</p>
        </div>
        <div class="content">
            <div class="note">
                This directory will be populated with confirmed participating employers before the event.
                <br><em>Acest director va fi completat cu angajatorii confirmati inainte de eveniment.</em>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Company / Companie</th>
                        <th>Country / Tara</th>
                        <th>Sector</th>
                        <th>Positions / Pozitii</th>
                    </tr>
                </thead>
                <tbody id="employerTable">
                    <!-- EMPLOYER_ROWS: will be populated by scripts or manually -->
                    <tr><td colspan="5" style="text-align:center; color:#999; padding:30px;">No employers registered yet / Niciun angajator inregistrat</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""


def update_index_page(county, date_str, venue, event_slug):
    """Insert new event into jobfair/index.html events list."""
    index_path = JOBFAIR_DIR / "index.html"
    if not index_path.exists():
        print(f"  WARNING: {index_path} not found, skipping index update")
        return False

    content = index_path.read_text(encoding='utf-8')
    date_ro = format_date_ro(date_str)
    date_en = format_date_en(date_str)

    event_html = f"""<li class="event-item">
                    <h4>
                        <span class="text-ro">Targ International — {county}</span>
                        <span class="text-en">International Job Fair — {county}</span>
                    </h4>
                    <div class="event-meta">
                        <span><strong><span class="text-ro">Data</span><span class="text-en">Date</span>:</strong> <span class="text-ro">{date_ro}</span><span class="text-en">{date_en}</span></span>
                        <span><strong><span class="text-ro">Locatie</span><span class="text-en">Venue</span>:</strong> {venue}</span>
                    </div>
                </li>
                <!-- EVENT_PLACEHOLDER"""

    # Replace the placeholder with actual event + new placeholder
    if '<!-- EVENT_PLACEHOLDER' in content:
        content = content.replace('<!-- EVENT_PLACEHOLDER: Events will be inserted here by create_event.py -->', event_html)

        # Remove the "no events" placeholder if it exists
        no_events_pattern = r'<li class="event-item">\s*<h4>\s*<span class="text-ro">Niciun eveniment.*?</li>'
        content = re.sub(no_events_pattern, '', content, flags=re.DOTALL)

        index_path.write_text(content, encoding='utf-8')
        return True

    print("  WARNING: EVENT_PLACEHOLDER not found in index.html")
    return False


def main():
    parser = argparse.ArgumentParser(description='Generate job fair event materials')
    parser.add_argument('--county', required=True, help='County name (e.g., Arges, Cluj)')
    parser.add_argument('--date', required=True, help='Event date YYYY-MM-DD')
    parser.add_argument('--venue', required=True, help='Venue name and address')
    parser.add_argument('--employers', type=int, default=30, help='Expected number of employers')
    parser.add_argument('--list', action='store_true', help='List existing events')
    args = parser.parse_args()

    if args.list:
        print("Existing events:")
        if EVENTS_DIR.exists():
            for d in sorted(EVENTS_DIR.iterdir()):
                if d.is_dir():
                    info_file = d / "event_info.json"
                    if info_file.exists():
                        info = json.loads(info_file.read_text())
                        print(f"  {d.name}: {info.get('county')} — {info.get('date')} — {info.get('venue')}")
                    else:
                        print(f"  {d.name}: (no event_info.json)")
        else:
            print("  No events directory yet.")
        return

    # Validate date
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
        return

    event_slug = f"{slugify(args.county)}_{args.date}"
    event_dir = EVENTS_DIR / event_slug
    event_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating job fair event: {args.county} — {args.date}")
    print(f"Venue: {args.venue}")
    print(f"Output: {event_dir}")
    print("-" * 50)

    # 1. Event info JSON
    event_info = {
        "county": args.county,
        "date": args.date,
        "venue": args.venue,
        "expected_employers": args.employers,
        "slug": event_slug,
        "created": datetime.now().isoformat(),
        "registration_url": REGISTRATION_URL,
        "worker_url": WORKER_URL,
        "status": "planned",
    }
    info_path = event_dir / "event_info.json"
    info_path.write_text(json.dumps(event_info, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"  Created: event_info.json")

    # 2. Posters (RO + EN)
    for lang in ['ro', 'en']:
        poster = generate_poster(args.county, args.date, args.venue, args.employers, lang)
        poster_path = event_dir / f"poster_{lang}.html"
        poster_path.write_text(poster, encoding='utf-8')
        print(f"  Created: poster_{lang}.html")

    # 3. Badges
    badges = generate_badges(args.county, args.date, args.venue)
    badges_path = event_dir / "badges.html"
    badges_path.write_text(badges, encoding='utf-8')
    print(f"  Created: badges.html")

    # 4. Employer list
    emp_list = generate_employer_list(args.county, args.date)
    emp_path = event_dir / "employer_list.html"
    emp_path.write_text(emp_list, encoding='utf-8')
    print(f"  Created: employer_list.html")

    # 5. Update index.html
    if update_index_page(args.county, args.date, args.venue, event_slug):
        print(f"  Updated: jobfair/index.html with new event")
    else:
        print(f"  SKIP: index.html not updated (manual edit needed)")

    print(f"\nDone! Event directory: {event_dir}")
    print(f"\nNext steps:")
    print(f"  1. Review generated files in {event_dir}")
    print(f"  2. Deploy jobfair/ to interjob.ro")
    print(f"  3. Send invitations: python send_invitations.py --event {event_slug}")


if __name__ == "__main__":
    main()
