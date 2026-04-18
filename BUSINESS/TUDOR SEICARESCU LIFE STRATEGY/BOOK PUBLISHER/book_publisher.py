"""Book Publisher — Data → KDP-ready PDF (interior + cover)."""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_DIR = SCRIPT_DIR / "templates"

# KDP trim sizes (width x height in inches)
TRIM_SIZES = {
    "6x9": ("6in", "9in"),
    "8.5x11": ("8.5in", "11in"),
    "a4": ("8.27in", "11.69in"),
    "a5": ("5.83in", "8.27in"),
}


def load_data(data_path, group_by="sector"):
    """Load CSV or JSON, return grouped sections."""
    path = Path(data_path)
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        # Handle nested formats
        if isinstance(raw, dict) and "employers" in raw:
            entries = raw["employers"]
        elif isinstance(raw, list):
            entries = raw
        else:
            entries = list(raw.values()) if isinstance(raw, dict) else []
    elif path.suffix == ".csv":
        with open(path, encoding="utf-8") as f:
            entries = list(csv.DictReader(f))
    else:
        print(f"Unsupported format: {path.suffix}")
        sys.exit(1)

    # Group by field
    groups = defaultdict(list)
    for e in entries:
        key = e.get(group_by, "Other") or "Other"
        if isinstance(key, list):
            key = key[0] if key else "Other"
        groups[key].append(e)

    sections = []
    for name in sorted(groups.keys()):
        items = sorted(groups[name], key=lambda x: (x.get("company") or x.get("name") or ""))
        sections.append({"name": name, "count": len(items), "entries": items})

    return sections, len(entries)


def render_html(template_name, context):
    """Render Jinja2 template to HTML string."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    tpl = env.get_template(template_name)
    return tpl.render(**context)


def html_to_pdf(html_content, output_path, width=None, height=None):
    """Convert HTML string to PDF using Playwright."""
    tmp_html = output_path.with_suffix(".html")
    tmp_html.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file:///{tmp_html.resolve()}")
        page.wait_for_load_state("networkidle")

        pdf_opts = {
            "path": str(output_path),
            "print_background": True,
            "prefer_css_page_size": True,
        }
        if width and height:
            pdf_opts["width"] = width
            pdf_opts["height"] = height

        page.pdf(**pdf_opts)
        browser.close()

    tmp_html.unlink()
    print(f"  PDF: {output_path} ({output_path.stat().st_size // 1024} KB)")


def generate_book(args):
    """Generate interior + cover PDFs."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    pw, ph = TRIM_SIZES.get(args.trim, TRIM_SIZES["8.5x11"])

    # Load data
    print(f"Loading data from {args.data}...")
    sections, total = load_data(args.data, args.group_by)
    print(f"  {total} entries in {len(sections)} sections")

    # Interior
    print("Generating interior...")
    interior_ctx = {
        "title": args.title,
        "subtitle": args.subtitle or "",
        "edition": args.edition or "First Edition, 2026",
        "publisher": args.publisher or "InterJob Research",
        "publisher_url": args.url or "https://cifn.eu",
        "contact_email": args.email or "office@cifn.eu",
        "about_publisher": args.about or "European recruitment and business intelligence.",
        "data_sources": args.sources or "Public records, government registries",
        "isbn": args.isbn or "",
        "year": "2026",
        "page_width": pw,
        "page_height": ph,
        "sections": sections,
        "total_entries": total,
    }
    interior_html = render_html("catalog_interior.html", interior_ctx)
    interior_pdf = output_dir / f"{slugify(args.title)}_interior.pdf"
    html_to_pdf(interior_html, interior_pdf, pw, ph)

    # Cover
    print("Generating cover...")
    # Cover is wider: front + spine + back + bleed
    # For now just front cover
    cover_ctx = {
        "title": args.title,
        "subtitle": args.subtitle or "",
        "edition": args.edition or "First Edition, 2026",
        "publisher": args.publisher or "InterJob Research",
        "cover_width": pw,
        "cover_height": ph,
        "cover_stats": [
            {"value": f"{total:,}", "label": "Companies"},
            {"value": str(len(sections)), "label": "Sectors"},
            {"value": "2026", "label": "Edition"},
        ],
    }
    cover_html = render_html("cover.html", cover_ctx)
    cover_pdf = output_dir / f"{slugify(args.title)}_cover.pdf"
    html_to_pdf(cover_html, cover_pdf, pw, ph)

    print(f"\nDone! Files in {output_dir}/")
    print(f"  Interior: {interior_pdf.name}")
    print(f"  Cover: {cover_pdf.name}")
    print(f"\nNext: upload to kdp.amazon.com")


def slugify(text):
    return text.lower().replace(" ", "_").replace("'", "")[:60]


def main():
    p = argparse.ArgumentParser(description="Book Publisher — Data to KDP PDF")
    p.add_argument("--data", required=True, help="CSV or JSON data file")
    p.add_argument("--title", required=True, help="Book title")
    p.add_argument("--subtitle", default="", help="Subtitle")
    p.add_argument("--trim", default="8.5x11", choices=TRIM_SIZES.keys())
    p.add_argument("--group-by", default="sector", help="Field to group entries")
    p.add_argument("--output", default="./output", help="Output directory")
    p.add_argument("--publisher", default="InterJob Research")
    p.add_argument("--edition", default="First Edition, 2026")
    p.add_argument("--url", default="https://cifn.eu")
    p.add_argument("--email", default="office@cifn.eu")
    p.add_argument("--about", default="European recruitment and business intelligence.")
    p.add_argument("--sources", default="Public records, government registries")
    p.add_argument("--isbn", default="")
    args = p.parse_args()
    generate_book(args)


if __name__ == "__main__":
    main()
