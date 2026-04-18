#!/usr/bin/env python3
"""
Split large catalog HTML into ~1.4MB parts for WSL Firefox PDF conversion.
Splits at sector-section boundaries to keep page breaks clean.
"""
import sys, io, os, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INPUT  = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR\jobs_catalog_april_tudor.html"
OUTDIR = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR"
MAX_MB = 1.4
MAX_BYTES = int(MAX_MB * 1024 * 1024)


def extract_head(html: str) -> str:
    """Extract everything up to and including <body>."""
    m = re.search(r'<body[^>]*>', html)
    if m:
        return html[:m.end()]
    return html[:html.find('<body') + 6]


def extract_foot(html: str) -> str:
    """Extract closing tags."""
    m = re.search(r'</body>', html, re.IGNORECASE)
    if m:
        return html[m.start():]
    return "</body></html>"


def split_at_sections(html: str) -> list:
    """Split on <section class="sector-section page-break"> boundaries."""
    marker = '<section class="sector-section page-break">'
    parts = html.split(marker)
    # parts[0] = head + cover + community + toc
    # parts[1..N] = sector blocks (need marker prepended)
    sections = [parts[0]] + [marker + p for p in parts[1:]]
    return sections


def main():
    with open(INPUT, encoding='utf-8') as f:
        html = f.read()

    file_mb = len(html.encode('utf-8')) / (1024*1024)
    print(f"Input: {file_mb:.1f}MB")

    head = extract_head(html)
    foot = extract_foot(html)
    sections = split_at_sections(html)

    print(f"Sections found: {len(sections)}")

    parts = []
    current_sections = []
    current_size = len(head.encode('utf-8')) + len(foot.encode('utf-8'))

    for sec in sections:
        sec_size = len(sec.encode('utf-8'))
        if current_size + sec_size > MAX_BYTES and current_sections:
            parts.append(current_sections)
            current_sections = [sec]
            current_size = len(head.encode('utf-8')) + len(foot.encode('utf-8')) + sec_size
        else:
            current_sections.append(sec)
            current_size += sec_size

    if current_sections:
        parts.append(current_sections)

    print(f"Will create {len(parts)} part(s)")

    out_paths = []
    for i, part_sections in enumerate(parts, 1):
        body_content = "".join(part_sections)
        # rebuild full HTML
        part_html = head + "\n" + body_content + "\n" + foot
        out_name = f"jobs_catalog_april_tudor_part{i}.html"
        out_path = os.path.join(OUTDIR, out_name)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(part_html)
        size_mb = len(part_html.encode('utf-8')) / (1024*1024)
        print(f"  Part {i}: {out_path} ({size_mb:.1f}MB)")
        out_paths.append(out_path)

    print(f"\n✓ Split complete. {len(parts)} files ready for PDF conversion.")
    return out_paths


if __name__ == "__main__":
    main()
