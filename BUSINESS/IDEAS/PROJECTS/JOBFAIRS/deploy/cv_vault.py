#!/usr/bin/env python3
"""CV Vault Manager — index, classify, match, merge CVs.
Local script (runs on laptop). Manages I:\DOCUMENTS\...\CV_VAULT\."""
import os, csv, json, re, shutil, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from datetime import datetime

VAULT = Path("I:/DOCUMENTS/INTERJOB SOLUTIONS EUROPE/2026/CV_VAULT")
ALL_DIR = VAULT / "all"
SKILL_DIR = VAULT / "by_skill"
INDEX_CSV = VAULT / "index.csv"
APPLICANT_DB = None  # Set if local copy exists

SKILL_KEYWORDS = {
    "welding": ["weld", "sudor", "mig", "mag", "tig", "smaw", "brazing"],
    "construction": ["construct", "build", "mason", "brick", "concrete", "cofraj",
                      "formwork", "plaster", "tiler", "faiantar", "zugrav", "painter"],
    "driver": ["driver", "sofer", "chauffeur", "truck", "camion", "forklift", "stivuitor"],
    "factory": ["factory", "machine", "operator", "assembly", "cnc", "lathe",
                "strungar", "packaging", "production", "manufacturing"],
    "horeca": ["cook", "chef", "waiter", "hotel", "restaurant", "kitchen", "housekeep",
               "cleaning", "barista"],
    "electrical": ["electric", "wiring", "panel", "plc", "automat"],
    "agriculture": ["farm", "agri", "harvest", "greenhouse", "livestock"],
}


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber or PyPDF2."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return " ".join(p.extract_text() or "" for p in pdf.pages)[:3000]
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(pdf_path))
        return " ".join(p.extract_text() or "" for p in reader.pages)[:3000]
    except Exception:
        pass
    return ""


def classify_skills(text):
    """Match text against skill keywords."""
    text_lower = text.lower()
    matches = []
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matches.append(skill)
    return matches or ["general"]


def extract_name(text, filename):
    """Try to extract name from CV text or filename."""
    # From filename
    name = filename.replace(".pdf", "").replace(".PDF", "")
    name = re.sub(r'^\d+_', '', name)  # Remove leading numbers
    name = re.sub(r'_cv$|_CV$|_resume$|_RESUME$', '', name, flags=re.I)
    name = name.replace("_", " ").strip()
    if len(name) > 3:
        return name[:80]
    # From text first line
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        return lines[0][:80]
    return filename[:50]


def extract_contact(text):
    """Extract email and phone from CV text."""
    email = ""
    phone = ""
    em = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    if em:
        email = em.group()
    ph = re.search(r'[\+]?[\d\s\-\(\)]{8,15}', text)
    if ph:
        phone = ph.group().strip()
    return email, phone


def extract_nationality(text, filename):
    """Guess nationality from text or filename."""
    countries = {
        "india": "IN", "pakistan": "PK", "nepal": "NP", "algeria": "DZ",
        "morocco": "MA", "romania": "RO", "turkmenistan": "TM",
        "bangladesh": "BD", "ethiopia": "ET", "rwanda": "RW",
        "mozambique": "MZ", "philippines": "PH", "togo": "TG",
        "burundi": "BI", "tunisia": "TN", "egypt": "EG", "italy": "IT",
    }
    combined = (text + " " + filename).lower()
    for country, code in countries.items():
        if country in combined:
            return code
    return "??"


def build_index():
    """Scan all CVs, extract info, build index.csv."""
    entries = []
    for pdf in sorted(ALL_DIR.glob("*.pdf")) + sorted(ALL_DIR.glob("*.PDF")):
        text = extract_text_from_pdf(pdf)
        name = extract_name(text, pdf.name)
        email, phone = extract_contact(text)
        nationality = extract_nationality(text, pdf.name)
        skills = classify_skills(text)

        entry = {
            "filename": pdf.name,
            "name": name,
            "email": email,
            "phone": phone,
            "nationality": nationality,
            "skills": "|".join(skills),
            "source": "vault_scan",
            "date_added": datetime.now().strftime("%Y-%m-%d"),
        }
        entries.append(entry)

        # Copy to skill folders
        for skill in skills:
            skill_folder = SKILL_DIR / skill
            skill_folder.mkdir(parents=True, exist_ok=True)
            dst = skill_folder / pdf.name
            if not dst.exists():
                shutil.copy2(pdf, dst)

        try:
            print(f"  {pdf.name[:40]:40s} -> {name[:25]:25s} {nationality} [{','.join(skills)}]")
        except UnicodeEncodeError:
            print(f"  {pdf.name[:40]} -> [non-latin name] {nationality} [{','.join(skills)}]")

    # Write index
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=entries[0].keys())
        w.writeheader()
        w.writerows(entries)
    print(f"\nIndex: {len(entries)} CVs -> {INDEX_CSV}")
    return entries


def match(skill, count=5):
    """Find candidates matching a skill."""
    if not INDEX_CSV.exists():
        print("Run 'build' first")
        return []
    with open(INDEX_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    matches = [r for r in rows if skill in r["skills"].split("|")]
    matches = matches[:count]
    for r in matches:
        print(f"  {r['name'][:30]:30s} {r['nationality']} {r['skills']:30s} {r['filename']}")
    print(f"\n{len(matches)} matches for '{skill}'")
    return matches


def merge_pack(client, skill, count=5):
    """Merge matching CVs into one PDF for client."""
    from PyPDF2 import PdfMerger
    matches = match(skill, count)
    if not matches:
        return
    merger = PdfMerger()
    for m in matches:
        path = ALL_DIR / m["filename"]
        if path.exists():
            merger.append(str(path))
    out_dir = VAULT.parent / "EXAMPLE CANDIDATES"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{client}_CANDIDATI_{skill.upper()}_{len(matches)}CV.pdf"
    merger.write(str(out_file))
    merger.close()
    print(f"\nMerged: {out_file} ({out_file.stat().st_size//1024}KB)")


def dedup():
    """Remove duplicate CVs by email. Keep newest."""
    if not INDEX_CSV.exists():
        print("Run 'build' first")
        return
    with open(INDEX_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen = {}
    dupes = []
    for r in rows:
        email_key = r["email"].lower().strip()
        if not email_key or email_key == "":
            continue
        if email_key in seen:
            dupes.append(r)
        else:
            seen[email_key] = r
    if not dupes:
        print("No duplicates found")
        return
    dupe_dir = VAULT / "duplicates"
    dupe_dir.mkdir(exist_ok=True)
    for d in dupes:
        src = ALL_DIR / d["filename"]
        if src.exists():
            shutil.move(str(src), str(dupe_dir / d["filename"]))
    # Also remove from skill folders
    for skill_dir in SKILL_DIR.iterdir():
        if skill_dir.is_dir():
            for d in dupes:
                f = skill_dir / d["filename"]
                if f.exists():
                    f.unlink()
    # Rewrite index without dupes
    clean = [r for r in rows if r not in dupes]
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=clean[0].keys())
        w.writeheader()
        w.writerows(clean)
    print(f"Removed {len(dupes)} duplicates. {len(clean)} unique CVs remain.")
    print(f"Dupes moved to {dupe_dir}")


def stats():
    """Show vault statistics."""
    if not INDEX_CSV.exists():
        print("Run 'build' first")
        return
    with open(INDEX_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Total CVs: {len(rows)}")
    skills_count = {}
    nat_count = {}
    for r in rows:
        for s in r["skills"].split("|"):
            skills_count[s] = skills_count.get(s, 0) + 1
        nat_count[r["nationality"]] = nat_count.get(r["nationality"], 0) + 1
    print("\nBy skill:")
    for s, c in sorted(skills_count.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")
    print("\nBy nationality:")
    for n, c in sorted(nat_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {n}: {c}")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "build":
        build_index()
    elif cmd == "match":
        skill = sys.argv[2] if len(sys.argv) > 2 else "general"
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        match(skill, count)
    elif cmd == "dedup":
        dedup()
    elif cmd == "pack":
        client = sys.argv[2] if len(sys.argv) > 2 else "CLIENT"
        skill = sys.argv[3] if len(sys.argv) > 3 else "general"
        count = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        merge_pack(client, skill, count)
    elif cmd == "stats":
        stats()
    else:
        print("Usage: cv_vault.py build|match <skill> [count]|pack <client> <skill> [count]|stats")
