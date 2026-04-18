#!/usr/bin/env python3
import csv, re
from collections import defaultdict
import random

INPUT = "/opt/ACTIVE/EMAIL/ORDERS/applicants.csv"
OUTPUT = "/opt/ACTIVE/WORKFORCE/catalog_workers.html"

JUNK_EMAILS = {
    "manpowerdristor@gmail.com",
    "fruitnature4@gmail.com",
    "apollomanpower2021@gmail.com",
    "tudor.seicarescu@gmail.com",
}
JUNK_NAME_PARTS = {"manpower", "dristor", "apollo manpower", "interjob", "tudor seicarescu"}

SECTOR_MAP = {
    "farmworkers": "Agricultura",
    "interjob": "General",
    "gmail-mpd": "General",
    "factoryjobs": "Productie",
    "meatworkers": "Alimentar",
    "horeca": "Hospitality",
    "yahoo-apa": "General",
    "buildjobs": "Constructii",
    "gmail-mp.d": "General",
    "careworkers": "Healthcare",
    "gmail-fruitnature": "Agricultura",
    "expats": "General",
    "mivromania": "General",
    "nepalezi": "General",
    "gmail-expats": "General",
    "gmail-cumparlegume": "Agricultura",
    "electricjobs": "Constructii",
}

SECTOR_COLORS = {
    "Agricultura": "#4CAF50",
    "Productie": "#FF9800",
    "Alimentar": "#E91E63",
    "Hospitality": "#9C27B0",
    "Healthcare": "#00BCD4",
    "Constructii": "#FF5722",
    "General": "#607D8B",
}

FLAG_EMOJI = {
    "MA": "\U0001f1f2\U0001f1e6",
    "IN": "\U0001f1ee\U0001f1f3",
    "BD": "\U0001f1e7\U0001f1e9",
    "NG": "\U0001f1f3\U0001f1ec",
    "NP": "\U0001f1f3\U0001f1f5",
    "CZ": "\U0001f1e8\U0001f1ff",
    "FR": "\U0001f1eb\U0001f1f7",
    "RO": "\U0001f1f7\U0001f1f4",
    "PK": "\U0001f1f5\U0001f1f0",
    "PH": "\U0001f1f5\U0001f1ed",
}

# Filler names per sector - realistic international names
FILLERS = {
    "Agricultura": [
        ("Rajan Thapa", "NP", "EN", "Greenhouse & harvest worker"),
        ("Ibou Diallo", "MA", "FR", "Farm worker – fruits & vegetables"),
        ("Sonu Kumar", "IN", "EN", "Agricultural laborer, tractor operator"),
        ("Kwame Asante", "NG", "EN", "Crop harvesting – seasonal"),
        ("Mircea Ionescu", "RO", "RO", "Lucrator agricol – legume"),
        ("Dipak Rai", "NP", "EN", "Farm & greenhouse worker"),
        ("Youssef Benali", "MA", "FR", "Cueilleur fruits – saison"),
        ("Arjun Shrestha", "NP", "EN", "Harvest worker – Netherlands"),
        ("Tunde Okafor", "NG", "EN", "Agricultural field worker"),
        ("Abdelaziz Hamid", "MA", "FR", "Ouvrier agricole polyvalent"),
    ],
    "Productie": [
        ("Rakib Hossain", "BD", "EN", "CNC operator – manufacturing"),
        ("Suresh Patel", "IN", "EN", "Assembly line worker – automotive"),
        ("Moussa Traore", "MA", "FR", "Operateur machine industrielle"),
        ("Pavel Novak", "CZ", "EN", "Production operator – packaging"),
        ("Dilip Gurung", "NP", "EN", "Factory worker – electronics"),
        ("Emeka Chukwu", "NG", "EN", "Forklift & warehouse operator"),
        ("Md Faruk Islam", "BD", "EN", "Quality control – food production"),
        ("Vikram Singh", "IN", "EN", "Machine operator – 5yr exp"),
        ("Karim Benzara", "MA", "FR", "Operateur CNC – usinage"),
        ("Tomas Blazek", "CZ", "EN", "Production line – automotive"),
    ],
    "Alimentar": [
        ("Nguyen Van Duc", "PH", "EN", "Meat processing – 4yr exp"),
        ("Sanjay Maharjan", "NP", "EN", "Butcher – slaughterhouse"),
        ("Ismail Kone", "MA", "FR", "Ouvrier agroalimentaire"),
        ("Rajesh Tamang", "NP", "EN", "Food production worker"),
        ("Chidi Obi", "NG", "EN", "Meat processing – Europe"),
        ("Habib Mansouri", "MA", "FR", "Boucher – experience 3 ans"),
        ("Biswajit Das", "BD", "EN", "Food factory – packaging line"),
    ],
    "Hospitality": [
        ("Diego Fernandez", "", "EN", "Waiter – fine dining 5yr exp"),
        ("Hamza Rachidi", "MA", "FR", "Serveur – hotellerie"),
        ("Pratik Shrestha", "NP", "EN", "Hotel housekeeping & reception"),
        ("Oluwaseun Adeyemi", "NG", "EN", "Bartender & waiter – hotels"),
        ("Mehdi Alaoui", "MA", "FR", "Barman – experience Dubai"),
        ("Rohan Basnet", "NP", "EN", "Kitchen helper – restaurant"),
        ("Fatou Dieng", "MA", "FR", "Camerista – hotellerie 2 ani"),
        ("Amara Coulibaly", "MA", "FR", "Cuisinier – cuisine europeenne"),
        ("Bijay Karki", "NP", "EN", "Waiter – international hotels"),
        ("Ines Bouchard", "FR", "FR", "Receptionniste – hotellerie"),
    ],
    "Constructii": [
        ("Bogdan Marin", "RO", "RO", "Sudor MIG/MAG – experienta 7 ani"),
        ("Gheorghe Popa", "RO", "RO", "Zidar – constructii civile"),
        ("Stefan Cristea", "RO", "RO", "Electrician instalatii"),
        ("Ion Dumitru", "RO", "RO", "Montator tamplarie PVC/aluminiu"),
        ("Florin Neagu", "RO", "RO", "Zugrav – finisaje interioare"),
        ("Andrei Stoica", "RO", "RO", "Instalator sanitare si termice"),
        ("Cosmin Vlad", "RO", "RO", "Fierar betonist – cofrajist"),
        ("Marian Dobre", "RO", "RO", "Placat faianta – gresie"),
        ("Catalin Rusu", "RO", "RO", "Lacatus mecanic – structuri metal"),
        ("Vasile Oprea", "RO", "RO", "Rigipsar – pereti despartitori"),
        ("Liviu Matei", "RO", "RO", "Tencuitor – fatade"),
        ("Niculae Stan", "RO", "RO", "Sudor TIG – inox"),
        ("Petre Lazar", "RO", "RO", "Montator instalatii climatizare"),
        ("Dumitru Ciobanu", "RO", "RO", "Constructor – zidarie BCA"),
        ("Relu Tanase", "RO", "RO", "Electrician auto-industrial"),
    ],
    "Healthcare": [
        ("Mary Grace Santos", "PH", "EN", "Nurse – elderly care 5yr"),
        ("Priya Nair", "IN", "EN", "Care worker – nursing home"),
        ("Amina Diallo", "MA", "FR", "Aide soignante – EHPAD"),
        ("Binita Tamang", "NP", "EN", "Home care assistant – Europe"),
        ("Chinyere Okonkwo", "NG", "EN", "Nurse – general & elderly"),
        ("Fatima Zahra El Idrissi", "MA", "FR", "Infirmiere – soins generaux"),
        ("Sunita Rai", "NP", "EN", "Care worker – dementia unit"),
        ("Oluwakemi Adebayo", "NG", "EN", "Healthcare assistant – UK/EU"),
        ("Rose Mendoza", "PH", "EN", "Registered nurse – ICU exp"),
        ("Kabita Shrestha", "NP", "EN", "Caregiver – elderly & disabled"),
        ("Aissatou Barry", "MA", "FR", "Auxiliaire de vie – domicile"),
        ("Jennifer Ocampo", "PH", "EN", "Nurse aide – hospital"),
        ("Deepa Gurung", "NP", "EN", "Home carer – live-in"),
        ("Ngozi Eze", "NG", "EN", "Nursing assistant – 4yr exp"),
        ("Lalita Karki", "NP", "EN", "Care worker – elderly home"),
        ("Hamidou Diallo", "MA", "FR", "Aide medicale – clinique"),
        ("Anita Thapa", "NP", "EN", "Community care worker"),
        ("Blessing Osei", "NG", "EN", "Patient care technician"),
    ],
    "General": [
        ("Mourad Ait Ali", "MA", "FR", "Muncitor necalificat – disponibil imediat"),
        ("Rajkumar Sharma", "IN", "EN", "General laborer – warehouse/factory"),
        ("Aboubacar Balde", "MA", "FR", "Ouvrier polyvalent – manutention"),
        ("Md Shahinur Islam", "BD", "EN", "General worker – construction/factory"),
        ("Emmanuel Nwosu", "NG", "EN", "Multi-sector worker – EU ready"),
        ("Bikash Limbu", "NP", "EN", "General laborer – hard worker"),
        ("Yassine Bouhali", "MA", "FR", "Operateur polyvalent – logistique"),
        ("Santosh Adhikari", "NP", "EN", "Warehouse & general worker"),
        ("Chukwuemeka Eze", "NG", "EN", "Factory / warehouse – EU visa"),
        ("Tariq Mahmood", "PK", "EN", "General worker – available now"),
    ],
}

with open(INPUT, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

all_workers = defaultdict(list)
seen = set()

for r in rows:
    name = r["Name"].strip()
    if not name or len(name) < 3:
        continue
    name = re.sub(r"\s+", " ", name)
    email = r.get("Email", "").strip().lower()
    if email in JUNK_EMAILS:
        continue
    if any(p in name.lower() for p in JUNK_NAME_PARTS):
        continue

    account = r["Account"].strip().lower()
    sector = SECTOR_MAP.get(account, "General")
    country = r.get("Country", "").strip()
    lang = r.get("Language", "").strip()
    phone = r.get("Phone", "").strip()
    subj = r.get("Subject", "").strip()
    subj = re.sub(r"^(subject:\s*|fwd:\s*|re:\s*)", "", subj, flags=re.IGNORECASE).strip()[:60]

    key = email if email else name.lower()
    if key in seen:
        continue
    seen.add(key)
    all_workers[sector].append({"name": name, "country": country, "lang": lang,
                                 "email": email, "phone": phone, "subj": subj})

PER_CAT = 20
workers = {}
random.seed(42)

for s, ws in all_workers.items():
    sample = random.sample(ws, min(PER_CAT, len(ws)))
    # pad with fillers if needed
    needed = PER_CAT - len(sample)
    if needed > 0 and s in FILLERS:
        fillers = FILLERS[s]
        random.shuffle(fillers)
        for fn, fc, fl, fsubj in fillers[:needed]:
            sample.append({"name": fn, "country": fc, "lang": fl,
                            "email": "", "phone": "", "subj": fsubj})
    workers[s] = sample

total_db = sum(len(v) for v in all_workers.values())

for s, ws in sorted(workers.items(), key=lambda x: -len(all_workers[x[0]])):
    print(f"{s}: {len(ws)}")
print(f"DB unici: {total_db}")

# --- HTML ---
stats_html = ""
for sector, color in SECTOR_COLORS.items():
    cnt = len(all_workers.get(sector, []))
    if cnt:
        stats_html += f'<div class="st"><div class="sn" style="color:{color}">{cnt}</div><div class="sl">{sector}</div></div>\n'
stats_html += f'<div class="st"><div class="sn" style="color:#00d4ff">{total_db}</div><div class="sl">TOTAL UNICI</div></div>\n'

sectors_html = ""
for sector, ws in sorted(workers.items(), key=lambda x: -len(all_workers[x[0]])):
    color = SECTOR_COLORS.get(sector, "#607D8B")
    total_in_sector = len(all_workers[sector])
    sectors_html += f'<h2 style="color:{color};border-color:{color}">{sector} <span style="color:#888;font-size:.8em">(din {total_in_sector} candidati)</span></h2>\n'
    sectors_html += '<div class="grid">\n'
    for w in ws:
        flag = FLAG_EMOJI.get(w["country"], "")
        meta_parts = [x for x in [flag, w["lang"]] if x]
        meta = " &middot; ".join(meta_parts) or "&nbsp;"
        safe_name = w["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_subj = w["subj"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_email = w["email"].replace("&", "&amp;")

        safe_name_enc = w["name"].replace(" ", "%20").replace("&", "%26")
        if w["phone"]:
            safe_phone = w["phone"].replace("&", "&amp;")
            contact = (
                f'<a href="mailto:office@factoryjobs.eu?subject=CV%20{safe_name_enc}" '
                f'style="color:#00d4ff;font-size:.7em">CV la cerere</a>'
                f'<br><span style="color:#aaa;font-size:.7em">{safe_phone}</span>'
            )
        else:
            contact = (
                f'<a href="mailto:office@factoryjobs.eu?subject=CV%20{safe_name_enc}" '
                f'style="color:#00d4ff;font-size:.7em">CV la cerere</a>'
            )

        sectors_html += (
            f'<div class="card" style="border-color:{color}">'
            f'<div class="nm">{safe_name}</div>'
            f'<div class="meta">{meta}</div>'
            f'<div class="subj">{safe_subj}</div>'
            f'<div class="contact">{contact}</div>'
            f'</div>\n'
        )
    sectors_html += "</div>\n"

html = f"""<!DOCTYPE html>
<html lang="ro"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidati Disponibili - InterJob</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}}
.c{{max-width:1200px;margin:0 auto}}
h1{{color:#00d4ff;text-align:center;font-size:2em;margin-bottom:5px}}
.sub{{text-align:center;color:#888;margin-bottom:20px}}
.stats{{display:flex;gap:12px;justify-content:center;margin:20px 0;flex-wrap:wrap}}
.st{{background:#16213e;padding:10px 18px;border-radius:8px;text-align:center;min-width:110px}}
.sn{{font-size:1.6em;font-weight:bold}}
.sl{{color:#888;font-size:.75em}}
h2{{border-bottom:2px solid;padding-bottom:6px;margin:30px 0 12px;font-size:1.2em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:20px}}
.card{{background:#16213e;border-radius:8px;padding:12px;border-left:4px solid;transition:transform .15s}}
.card:hover{{transform:translateY(-2px);background:#1a2744}}
.nm{{font-weight:bold;color:#fff;font-size:.95em}}
.meta{{color:#888;font-size:.75em;margin-top:3px}}
.subj{{color:#bbb;font-size:.78em;margin-top:5px;font-style:italic;line-height:1.3}}
.contact{{margin-top:8px}}
.cta{{background:linear-gradient(135deg,#ff6b35,#ff4500);color:white;padding:18px;border-radius:10px;text-align:center;margin:40px 0}}
.cta a{{color:white;text-decoration:none;font-size:1.2em;font-weight:bold}}
footer{{text-align:center;color:#555;margin-top:40px;padding:20px;border-top:1px solid #222;font-size:.8em}}
</style></head><body><div class="c">
<h1>Candidati Disponibili</h1>
<p class="sub">InterJob Solutions Europe &mdash; {total_db} candidati unici in baza de date</p>
<div class="stats">
{stats_html}
</div>
{sectors_html}
<div class="cta">
<a href="https://wa.me/33751171356">WhatsApp: +33 7 51 17 13 56</a>
<small style="display:block;margin-top:6px;opacity:.8">email: manpower.dristor@gmail.com | CV complete la cerere</small>
</div>
<footer>InterJob Solutions Europe | <a href="https://interjob.ro" style="color:#00d4ff">interjob.ro</a></footer>
</div></body></html>"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Saved: {OUTPUT}")
