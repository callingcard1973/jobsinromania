import os
import shutil

BASE = r"D:\MEMORY\CAMPAIGNS"
SRC = r"D:\MEMORY\BUSINESS\BOGDAN GAVRA"
EMAIL_SRC = r"D:\MEMORY\CAMPAIGNS\EMAIL"

# Create directory structure
dirs = [
    r"DATA\RO", r"DATA\EU", r"DATA\B2B", r"DATA\SENT",
    r"CODE\senders", r"CODE\scrapers", r"CODE\enrichment", r"CODE\utils",
    r"TEMPLATES\RO", r"TEMPLATES\EU", r"TEMPLATES\B2B", r"TEMPLATES\WORKERS",
    r"LOGS",
]
for d in dirs:
    os.makedirs(os.path.join(BASE, d), exist_ok=True)

copied = []
skipped = []

def copy_file(src_path, dst_path):
    if os.path.exists(src_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)
        copied.append(f"{src_path} -> {dst_path}")
    else:
        skipped.append(src_path)

# Files from BOGDAN GAVRA
bg = SRC
copies = [
    (r"primarii_campanie_enriched.csv", r"DATA\RO\primarii_campanie_enriched.csv"),
    (r"primarii_campanie.csv",          r"DATA\RO\primarii_campanie.csv"),
    (r"primarii_mayor_lookup.csv",      r"DATA\RO\primarii_mayor_lookup.csv"),
    (r"sicap_defrisare_leads.csv",      r"DATA\RO\sicap_defrisare_leads.csv"),
    (r"email_template_primarii.txt",    r"TEMPLATES\RO\primarii_parcuri.txt"),
    (r"email_furnizori_gazon.txt",      r"TEMPLATES\B2B\furnizori_gazon_en.txt"),
    (r"campaign_primarii.py",           r"CODE\senders\campaign_primarii.py"),
    (r"sicap_monitor.py",               r"CODE\scrapers\sicap_monitor.py"),
    (r"sicap_defrisare_monitor.py",     r"CODE\scrapers\sicap_defrisare_monitor.py"),
    (r"sicap_monitor_gazon.py",         r"CODE\scrapers\sicap_monitor_gazon.py"),
    (r"apm_defrisare_scraper.py",       r"CODE\scrapers\apm_defrisare_scraper.py"),
    (r"merge_primarii.py",              r"CODE\enrichment\merge_primarii.py"),
    (r"scrape_primari.py",              r"CODE\enrichment\scrape_primari.py"),
    (r"scrape_partide.py",              r"CODE\enrichment\scrape_partide.py"),
    (r"campaign_primarii.log",          r"LOGS\campaign_primarii.log"),
]
for src_rel, dst_rel in copies:
    copy_file(os.path.join(bg, src_rel), os.path.join(BASE, dst_rel))

# From EMAIL dir
copy_file(
    os.path.join(EMAIL_SRC, "ebrd_template_ro.txt"),
    os.path.join(BASE, r"TEMPLATES\EU\ebrd_template_ro.txt")
)

# Other .txt templates from EMAIL (skip known non-templates)
skip_names = {"COMPLETION_STATUS.txt", "ebrd_romania_needs_analysis.txt", "ebrd_template_ro.txt"}
for fname in os.listdir(EMAIL_SRC):
    if fname.endswith(".txt") and fname not in skip_names:
        dst = os.path.join(BASE, "TEMPLATES", "EU", fname)
        copy_file(os.path.join(EMAIL_SRC, fname), dst)

print("=== COPIED ===")
for c in copied:
    print(c)
print("\n=== SKIPPED (not found) ===")
for s in skipped:
    print(s)
