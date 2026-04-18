#!/usr/bin/env python3
"""
Hi-Profile Employer Scorer — 18 criteria
Reads ANOFM CSV, enriches from DB, scores, outputs ranked list.
Usage: python3 hi_profile_scorer.py [--min-score 30]
"""
import csv, psycopg2, sys, sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

ANOFM = "/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/anofm_raw_20260414_163001.csv"
OUTPUT = "/opt/ACTIVE/WORKFORCE/hi_profile_scored.csv"
DB = "dbname=interjob_master"
APPLICANTS_DB = "/mnt/hdd/OPENDATA/DATA/master_applicants.db"
DNC_FILE = "/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv"

PERSONAL = {"gmail.com","yahoo.com","yahoo.ro","hotmail.com",
    "outlook.com","icloud.com","live.com","ymail.com",
    "yahoo.co.uk","mail.com","aol.com","protonmail.com"}

BRANDS = {"leoni.com","draexlmaier.com","harting.com",
    "delonghigroup.com","arabesque.ro","romstal.ro",
    "terasteel.ro","em.ro","hidroelectrica.ro",
    "transelectrica.ro","romcim.ro","holcim.com",
    "strabag.com","unicarm.ro","scandia.ro","harmopan.ro",
    "boromir.ro","carmistin.ro","sergiana.ro","aldahra.com",
    "asahibeer.ro","selgros.ro","fancourier.ro","flanco.ro",
    "continentalhotels.ro","accor.com","hilton.com",
    "reginamaria.ro","medicover.ro","primark.com"}

BLUE_COLLAR = set(range(10,34))|set(range(41,44))|set(range(49,54))
DEFICIT = set(range(41,44))|{55,56}|{1,2,3}  # constr+horeca+agri

def load_anofm():
    co = defaultdict(lambda: {"emails":set(),"phones":set(),
        "contacts":set(),"jobs":set(),"total_pos":0,
        "domains":set(),"locations":set(),"deadlines":[],
        "salaries":[],"max_per_job":0,"website":"",
        "sources":set()})
    with open(ANOFM, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            n = r.get("company_name","").strip()
            if not n: continue
            d = co[n]
            for ef in ["email_1","email_2","email_3"]:
                e = r.get(ef,"").strip()
                if e and "@" in e:
                    d["emails"].add(e)
                    d["domains"].add(e.split("@")[1].lower())
                    break
            for pf in ["phone_1","phone_2","phone_3"]:
                p = r.get(pf,"").strip()
                if p and len(p)>5: d["phones"].add(p)
            for cf in ["contact_person_1","contact_person_2"]:
                c = r.get(cf,"").strip()
                if c and len(c)>3: d["contacts"].add(c)
            job = r.get("job_title","").strip()
            if job: d["jobs"].add(job)
            try: pos = int(r.get("positions_available","1"))
            except: pos = 1
            d["total_pos"] += pos
            if pos > d["max_per_job"]: d["max_per_job"] = pos
            loc = r.get("company_city","").strip()
            if loc: d["locations"].add(loc)
            dl = r.get("application_deadline","").strip()
            if dl: d["deadlines"].append(dl)
            for sf in ["salary_min","salary_max"]:
                try: d["salaries"].append(float(r.get(sf,0)))
                except: pass
            w = r.get("company_website","").strip()
            if w and len(w)>5: d["website"] = w
            src = r.get("scrape_date","").strip()
            if src: d["sources"].add(src[:7])  # YYYY-MM
    return co

def load_dnc():
    dnc = set()
    try:
        with open(DNC_FILE) as f:
            for line in f:
                dnc.add(line.strip().lower())
    except: pass
    return dnc

def load_responded():
    resp = set()
    try:
        with open("/opt/ACTIVE/EMAIL/ORDERS/orders.csv",
                  encoding="utf-8") as f:
            for line in f:
                parts = line.split(",")
                for p in parts:
                    if "@" in p:
                        resp.add(p.strip().lower())
    except: pass
    return resp

def enrich(companies):
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    # Insolvency DISABLED
    # cur.execute("SELECT UPPER(company_name) FROM insolvency "
    #            "WHERE company_name IS NOT NULL")
    insolv = set()

    for n in companies:
        companies[n]["insolvent"] = n.upper() in insolv
        cur.execute("""
            SELECT revenue, employees_count, cui, caen,
                   public_contracts_value
            FROM master_romania_companies
            WHERE UPPER(name) = UPPER(%s)
            ORDER BY revenue DESC NULLS LAST LIMIT 1
        """, (n,))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                SELECT revenue, employees_count, cui, caen,
                       public_contracts_value
                FROM master_romania_companies
                WHERE UPPER(name) LIKE UPPER(%s)
                ORDER BY revenue DESC NULLS LAST LIMIT 1
            """, (n[:25]+"%",))
            row = cur.fetchone()
        if row:
            companies[n]["revenue"] = float(row[0] or 0)
            companies[n]["employees"] = int(row[1] or 0)
            companies[n]["cui"] = row[2] or ""
            companies[n]["caen"] = row[3] or ""
            companies[n]["contracts"] = float(row[4] or 0)
    cur.close(); conn.close()

def score(d, dnc, responded):
    s = 0
    # 1 Positions (25)
    p = d["total_pos"]
    s += 25 if p>50 else 20 if p>20 else 15 if p>5 else 5

    # 2 Revenue (20)
    r = d.get("revenue",0)
    s += 20 if r>100e6 else 15 if r>50e6 else 10 if r>10e6 else 5 if r>1e6 else 0

    # 3 Employees (15)
    e = d.get("employees",0)
    s += 15 if e>500 else 10 if e>200 else 5 if e>50 else 0

    # 4 Public contracts (10)
    c = d.get("contracts",0)
    s += 10 if c>1e6 else 5 if c>0 else 0

    # 5 Corporate email (10)
    corp = not all(x in PERSONAL for x in d["domains"]) if d["domains"] else False
    s += 10 if corp else 0

    # 6 Distinct jobs (10)
    j = len(d["jobs"])
    s += 10 if j>10 else 8 if j>5 else 5 if j>2 else 2

    # 7 Blue-collar sector (5)
    try:
        cn = int(d.get("caen","")[:2])
        s += 5 if cn in BLUE_COLLAR else 0
    except: pass

    # 8 Brand (5)
    s += 5 if any(x in BRANDS for x in d["domains"]) else 0

    # 9 Recurenta (10) — posted in 3+ months
    months = len(d["sources"])
    s += 10 if months>=3 else 5 if months>=2 else 0

    # 10 Locations (8)
    loc = len(d["locations"])
    s += 8 if loc>=5 else 5 if loc>=3 else 2 if loc>=2 else 0

    # 11 Salary (8)
    sal = max(d["salaries"]) if d["salaries"] else 0
    s += 8 if sal>6000 else 5 if sal>4000 else 2 if sal>2500 else 0

    # 12 Deadline within 30 days (7)
    now = datetime.now()
    for dl in d["deadlines"]:
        try:
            dt = datetime.strptime(dl[:10], "%Y-%m-%d")
            if 0 < (dt - now).days <= 30:
                s += 7; break
        except: pass

    # 13 Positions per job 5+ (5)
    s += 5 if d["max_per_job"] >= 5 else 0

    # 14 Has website (3)
    s += 3 if d["website"] else 0

    # 15 Insolvent (-20)
    # if d.get("insolvent"): s -= 20

    # 16 In DNC/bounce (-10)
    if any(e.lower() in dnc for e in d["emails"]): s -= 10

    # 17 Previously responded (+15)
    if any(e.lower() in responded for e in d["emails"]): s += 15

    # 18 Deficit sector (5)
    try:
        cn = int(d.get("caen","")[:2])
        s += 5 if cn in DEFICIT else 0
    except: pass

    return s

def main():
    ms = 30
    if "--min-score" in sys.argv:
        ms = int(sys.argv[sys.argv.index("--min-score")+1])

    print("Loading ANOFM..."); co = load_anofm()
    print(f"  {len(co)} employers")
    print("Loading DNC..."); dnc = load_dnc()
    print("Loading responses..."); resp = load_responded()
    print("Enriching from DB..."); enrich(co)
    print("Scoring...")

    scored = []
    for n, d in co.items():
        sc = score(d, dnc, resp)
        if sc >= ms: scored.append((n, sc, d))
    scored.sort(key=lambda x: -x[1])

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["score","company","positions","revenue",
            "employees","cui","caen","contracts","jobs",
            "locations","salary_max","website","insolvent",
            "contacts","emails","phones"])
        for n, sc, d in scored:
            w.writerow([sc, n, d["total_pos"],
                int(d.get("revenue",0)),
                d.get("employees",0), d.get("cui",""),
                d.get("caen",""), int(d.get("contracts",0)),
                len(d["jobs"]), len(d["locations"]),
                int(max(d["salaries"])) if d["salaries"] else 0,
                d["website"], d.get("insolvent",False),
                "; ".join(sorted(d["contacts"])),
                "; ".join(sorted(d["emails"])),
                "; ".join(sorted(d["phones"]))])

    print(f"\n{len(scored)} employers (score >= {ms})")
    print(f"Saved: {OUTPUT}\n")
    for n, sc, d in scored[:25]:
        rv = d.get("revenue",0)/1e6
        print(f"{sc:>3} | {n[:42]:42} | {d['total_pos']:>3} poz"
              f" | {rv:>7.1f}M | {d.get('employees',0):>5} ang")

if __name__ == "__main__":
    main()
