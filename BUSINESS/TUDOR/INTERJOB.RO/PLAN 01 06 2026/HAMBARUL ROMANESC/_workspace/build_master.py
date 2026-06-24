#!/usr/bin/env python3
"""Build HAMBARUL ROMANESC supplier master from reused assets (VIA-PROFI + SILOZURI)."""
import csv, re, os
from collections import defaultdict

BASE = r"D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026"
OUT = r"D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\HAMBARUL ROMANESC\_workspace"
VIA = os.path.join(BASE, "SUPERMARKETURI", "FURNIZORI", "DATA", "via_profi_producers_full_detailed.csv")
SILO = os.path.join(BASE, "SILOZURI", "DATA", "MASTER.csv")
TIER1 = os.path.join(BASE, "SILOZURI", "DATA", "MASTER_TIER1_READY_TO_CALL.csv")

PLACEHOLDER = "via.profi@profi.ro"

# category classifier from free-text products/name
def classify(txt):
    t = (txt or "").lower()
    if re.search(r"miere|apicol|stupina", t): return "honey"
    if re.search(r"vin|tuica|tuică|tzuica|palinc|distil|crama|cramă|podgor", t): return "wine/tuica"
    if re.search(r"branz|brânz|cascaval|caşcaval|lapte|lactat|smantana|smântân|iaurt|telemea", t): return "dairy"
    if re.search(r"carne|porc|vita|vită|pui|mezel|carnati|cârnati|salam|charcut|abator|macel", t): return "meat/charcuterie"
    if re.search(r"oua|ouă", t): return "eggs"
    if re.search(r"paine|pâine|brutar|panif|cozonac|patiser|covrig", t): return "bakery"
    if re.search(r"zacusc|gem|dulcea|dulceaţ|murat|conserv|compot|bulion|sirop|pasta de", t): return "preserves/conserve"
    if re.search(r"legum|fruct|fructe|cartof|rosii|roşii|capsun|capşun|mar |mere|struguri|ceapa|usturoi|varza|varză|vegetal", t): return "produce/vegetables"
    if re.search(r"cereal|grau|grâu|porumb|floarea|orz|rapita|rapiţă|soia|siloz|graunte", t): return "cereals/grain"
    return "other/traditional"

# Romanian-origin verification via CAEN (silozuri) — cultivation/manuf NACE
def origin_from_caen(caen):
    if not caen: return False
    c = str(caen).strip()
    # 01xx cultivation/animal, 10xx-11xx food/beverage manuf, 03xx fishing
    return bool(re.match(r"^(01|03|10|11)", c))

rows = []
src_counts = defaultdict(int)
seen_cui = {}      # cui -> idx in rows
seen_nc = {}       # (name,county) -> idx

def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())

def add(rec):
    cui = (rec["cui"] or "").strip()
    key_nc = (norm(rec["name"]), norm(rec["county"]))
    if cui and cui in seen_cui:
        return False
    if not cui and key_nc in seen_nc:
        return False
    if cui: seen_cui[cui] = len(rows)
    seen_nc[key_nc] = len(rows)
    rows.append(rec)
    return True

# --- VIA-PROFI producers ---
with open(VIA, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        name = r["name"].strip()
        if not name: continue
        prod = (r.get("products") or "").strip()
        cat = classify(prod + " " + name)
        email = (r.get("email") or "").strip()
        if email.lower() == PLACEHOLDER: email = ""   # hidden placeholder, not real
        phone = (r.get("phone") or "").strip()
        contact = 1 if (email or phone) else 0
        # fit score: producer-verified origin (VIA-PROFI = vetted RO producer directory)
        fit = 50
        if email: fit += 20
        if phone: fit += 15
        if cat in ("produce/vegetables","dairy","meat/charcuterie","honey","preserves/conserve","eggs","wine/tuica","bakery"): fit += 15
        fit = min(fit, 100)
        add({"cui":"","name":name,"county":r.get("county","").strip().title(),
             "category":cat,"products":prod,"email":email,"phone":phone,
             "capacity":"","certifications":"",
             "origin_verified":"True",  # VIA-PROFI = verified producer directory (mic producator)
             "fit_score":str(fit),"source":"VIA-PROFI"})
        src_counts["VIA-PROFI"] += 1

# --- SILOZURI: TIER_1 first (ready to contact), then rest of MASTER ---
tier1_cuis = set()
def load_silo(path, tag):
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            name = r["name"].strip()
            if not name: continue
            cui = (r.get("cui") or "").strip()
            caen = (r.get("caen") or "").strip()
            cap = r.get("capacity_total_t","0") or "0"
            cat = "cereals/grain"
            email = (r.get("email") or "").strip()
            phone = (r.get("phone") or "").strip()
            origin = origin_from_caen(caen)
            fit = 40
            if r.get("_quality_tier","").startswith("TIER_1"): fit += 25
            if email: fit += 15
            if phone: fit += 10
            try:
                if float(cap) > 1000: fit += 10
            except: pass
            if origin: fit += 5
            fit = min(fit,100)
            if add({"cui":cui,"name":name,"county":(r.get("county") or "").strip().title(),
                    "category":cat,"products":"cereale/grâne (siloz)","email":email,"phone":phone,
                    "capacity":cap,"certifications":"",
                    "origin_verified":str(origin),
                    "fit_score":str(fit),"source":tag}):
                src_counts[tag] += 1

load_silo(TIER1, "SILOZURI_TIER1")
for c in seen_cui: tier1_cuis.add(c)
load_silo(SILO, "SILOZURI_MASTER")

# write master
os.makedirs(OUT, exist_ok=True)
cols = ["cui","name","county","category","products","email","phone","capacity","certifications","origin_verified","fit_score","source"]
with open(os.path.join(OUT,"01_suppliers_master.csv"),"w",encoding="utf-8-sig",newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

# summary
by_cat = defaultdict(int); by_cat_county = defaultdict(lambda: defaultdict(int))
with_email = with_phone = origin_t = 0
for r in rows:
    by_cat[r["category"]] += 1
    by_cat_county[r["category"]][r["county"] or "?"] += 1
    if r["email"]: with_email += 1
    if r["phone"]: with_phone += 1
    if r["origin_verified"]=="True": origin_t += 1

counties = sorted({r["county"] for r in rows if r["county"]})
print(f"TOTAL rows: {len(rows)}")
print(f"sources: {dict(src_counts)}")
print(f"with_email: {with_email}  with_phone: {with_phone}  origin_verified: {origin_t}")
print(f"counties: {len(counties)}")
for c in sorted(by_cat, key=lambda k:-by_cat[k]): print(f"  {c}: {by_cat[c]}")

# write summary md
TARGET = ["produce/vegetables","dairy","meat/charcuterie","bakery","preserves/conserve","honey","eggs","wine/tuica","other/traditional","cereals/grain"]
with open(os.path.join(OUT,"01_suppliers_summary.md"),"w",encoding="utf-8") as f:
    f.write("# HAMBARUL ROMANESC — Supplier Master Coverage Summary\n\n")
    f.write("Generated from reused assets (VIA-PROFI + SILOZURI). No new scraping.\n\n")
    f.write(f"- **Total unique suppliers:** {len(rows)}\n")
    f.write("- **Sources:** " + ", ".join(f"{k}={v}" for k,v in src_counts.items()) + "\n")
    f.write(f"- **With email:** {with_email} ({100*with_email//len(rows)}%)  |  **With phone:** {with_phone} ({100*with_phone//len(rows)}%)\n")
    f.write(f"- **Origin verified:** {origin_t} ({100*origin_t//len(rows)}%)\n")
    f.write(f"- **Counties covered:** {len(counties)}\n\n")
    f.write("## By category\n\n| Category | Count | With email | With phone |\n|---|---|---|---|\n")
    for c in sorted(by_cat, key=lambda k:-by_cat[k]):
        ce = sum(1 for r in rows if r["category"]==c and r["email"])
        cp = sum(1 for r in rows if r["category"]==c and r["phone"])
        f.write(f"| {c} | {by_cat[c]} | {ce} | {cp} |\n")
    f.write("\n## Category x County (top counties per category)\n\n")
    for c in sorted(by_cat, key=lambda k:-by_cat[k]):
        top = sorted(by_cat_county[c].items(), key=lambda kv:-kv[1])[:8]
        f.write(f"- **{c}**: " + ", ".join(f"{cty}({n})" for cty,n in top) + "\n")
    f.write("\n## GAPS (food categories for a supermarket assortment)\n\n")
    food = ["produce/vegetables","dairy","meat/charcuterie","bakery","preserves/conserve","honey","eggs","wine/tuica"]
    for c in food:
        n = by_cat.get(c,0)
        flag = "CRITICAL GAP" if n==0 else ("THIN" if n<15 else "ok")
        f.write(f"- {c}: {n} suppliers — {flag}\n")
    f.write("\n**Note:** Cereals/grain dominates (SILOZURI reuse). Fresh-food categories (dairy, meat, bakery, eggs) are thin — these require targeted producer scraping (MADR producer registry, ANSVSA, local farm directories) in a follow-up sourcing pass. VIA-PROFI `via.profi@profi.ro` placeholder emails were nulled (real email hidden behind directory).\n")
print("WROTE master + summary")
