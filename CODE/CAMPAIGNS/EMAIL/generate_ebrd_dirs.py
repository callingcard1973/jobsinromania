#!/usr/bin/env python3
"""Generate EBRD project directories with CLAUDE.md for each."""
import os, re
from collections import Counter

base = "D:/MEMORY/BERD EBRD"
raw = open(f"{base}/ebrd_active_raw.txt", encoding="utf-8").read().strip().split("\n")

projects = []
for line in raw:
    if not line.strip(): continue
    parts = line.split("|||")
    if len(parts) < 13: continue
    projects.append({
        "psd_id": parts[0].strip(),
        "title": parts[1].strip(),
        "sector": parts[2].strip(),
        "status": parts[3].strip() or "In Progress",
        "finance": parts[4].strip(),
        "total_cost": parts[5].strip(),
        "contact_name": parts[6].strip(),
        "contact_email": parts[7].strip(),
        "contact_phone": parts[8].strip(),
        "contact_website": parts[9].strip(),
        "contact_address": parts[10].strip(),
        "overview": parts[11].strip(),
        "url": parts[12].strip(),
    })

print(f"Parsed {len(projects)} projects")

def analyze_needs(sector, title, overview):
    text = f"{title} {overview}".lower()
    w, m, s = [], [], []

    if sector == "Energy":
        if "wind" in text or "eolian" in text:
            w = ["Montatori turbine eoliene", "Electricieni industriali MT/IT", "Sudori autorizati", "Operatori macarale", "Muncitori constructii civile (fundatii beton)", "Personal securitate santier"]
            m = ["Beton armat (fundatii turbine)", "Cabluri electrice MT", "Structuri metalice", "Transformatoare", "Drumuri acces (pietris, asfalt)"]
            s = ["Transport componente supradimensionate", "Studii geotehnice", "Proiectare electrica"]
        elif "solar" in text or "pv" in text:
            w = ["Montatori panouri fotovoltaice", "Electricieni MT/JT", "Muncitori constructii civile", "Operatori utilaje"]
            m = ["Structuri metalice galvanizate (trackere/fixe)", "Cabluri solare DC + AC", "Invertoare", "Transformatoare", "Garduri perimetrale"]
            s = ["Topografie", "Proiectare electrica", "Conectare la retea"]
        elif "bess" in text or "battery" in text or "storage" in text:
            w = ["Electricieni industriali specializati", "Tehnicieni sisteme baterii", "Montatori", "Muncitori constructii civile"]
            m = ["Module baterii Li-ion", "Sisteme de racire", "Transformatoare", "Cabluri MT", "Containere metalice"]
            s = ["Proiectare electrica", "Testare si punere in functiune"]
        elif "nuclear" in text or "cernavoda" in text:
            w = ["Sudori autorizati nuclear (ASME)", "Tehnicieni nucleari", "Ingineri proces"]
            m = ["Echipamente specializate nucleare", "Oteluri speciale"]
            s = ["Consultanta nucleara", "Certificari CNCAN"]
        elif "distribut" in text or "grid" in text or "delgaz" in text:
            w = ["Electricieni retele distributie", "Montatori stalpi/linii", "Operatori utilaje (nacele)"]
            m = ["Stalpi beton/metal", "Conductoare electrice", "Transformatoare distributie", "Contoare smart"]
            s = ["Proiectare retele", "Avize ANRE"]
        else:
            w = ["Electricieni", "Muncitori constructii", "Sudori"]
            m = ["Echipamente energetice", "Cabluri", "Transformatoare"]
            s = ["Proiectare", "Consultanta energetica"]

    elif sector == "Municipal Infrastructure":
        if any(x in text for x in ["water", "wastewater", "apa ", "swift", "canalizare", "epurare"]):
            w = ["Instalatori apa/canal", "Sudori PE-HD", "Muncitori sapaturi", "Operatori excavatoare/buldozere", "Electricieni (statii pompare)"]
            m = ["Tevi PE-HD (apa potabila)", "Tevi PVC/GRP (canalizare)", "Statii de pompare complete", "Componente statii epurare", "Vane, hidranti, robinete", "Camine vizitare beton"]
            s = ["Proiectare retele apa/canal", "Studii hidrogeologice", "Dezinfectie / punere in functiune"]
        elif any(x in text for x in ["district heating", "termoficare", " dh "]):
            w = ["Sudori conducte termoficare", "Izolatori conducte", "Instalatori termice", "Muncitori sapaturi"]
            m = ["Conducte preizolate", "Schimbatoare de caldura", "Pompe circulatie", "Vane de reglare"]
            s = ["Proiectare termotehnica", "Echilibrare hidraulica retea"]
        elif any(x in text for x in ["building", "rehabilitation", "energy efficiency", "green building"]):
            w = ["Zugravi/vopsitori", "Montatori tamplarie PVC/AL", "Izolatori termici", "Tinichigii", "Electricieni", "Instalatori HVAC"]
            m = ["Polistiren expandat/extrudat", "Vata minerala bazaltica", "Tamplarie termoizolanta", "Adezivi, tencuieli decorative", "Pompe de caldura"]
            s = ["Audit energetic", "Proiectare reabilitare", "Certificare energetica"]
        elif any(x in text for x in ["transport", "road", "drum", "bus", "tram"]):
            w = ["Asfaltatori", "Operatori utilaje drumuri", "Pavatori", "Muncitori constructii civile"]
            m = ["Mixtura asfaltica", "Borduri beton", "Semnalistica rutiera", "Agregate minerale"]
            s = ["Proiectare drumuri", "Studii de trafic", "Dirigentare santier"]
        else:
            w = ["Muncitori constructii civile", "Instalatori", "Electricieni"]
            m = ["Beton, otel, ciment", "Materiale constructii"]
            s = ["Proiectare", "Dirigentare"]

    elif sector == "Real Estate":
        if any(x in text for x in ["cold", "frigorific", "newcold"]):
            w = ["Fierari betonieri", "Dulgheri cofraje", "Montatori structuri metalice", "Sudori", "Tehnicieni frigorifici", "Electricieni industriali"]
            m = ["Panouri izolate frigorifice (PIR/PUR)", "Echipamente frigorifice industriale", "Rafturi depozit automatizat", "Structuri metalice", "Beton industrial"]
            s = ["Proiectare frigorifica", "Automatizare depozit", "Certificare HACCP"]
        elif any(x in text for x in ["logist", "warehouse", "wdp", "industrial"]):
            w = ["Montatori structuri metalice (hale)", "Betonieri (platfome)", "Electricieni", "Instalatori"]
            m = ["Structuri metalice prefabricate", "Panouri sandwich", "Beton industrial", "Usi sectionale industriale", "Rampe incarcare"]
            s = ["Proiectare hale", "Sisteme sprinkler", "Consultanta logistica"]
        else:
            w = ["Fierari betonieri", "Dulgheri", "Zugravi", "Electricieni", "Instalatori", "Montatori fatade"]
            m = ["Otel beton", "Cofraj", "Beton", "Tamplarie", "Fatade ventilate"]
            s = ["Proiectare", "Dirigentare", "Certificare"]

    elif sector == "Food and Agribusiness":
        if any(x in text for x in ["bak", "bread", "lantm", "brutari"]):
            w = ["Muncitori constructie fabrica", "Montatori echipamente industriale", "Electricieni", "Muncitori productie panificatie"]
            m = ["Cuptoare industriale panificatie", "Linii ambalare automata", "Sisteme transport intern (benzi)", "Echipamente frigorifice", "Silozuri faina"]
            s = ["Proiectare fabrica alimentara", "Certificare HACCP/IFS/BRC"]
        elif any(x in text for x in ["meat", "carne", "cris"]):
            w = ["Muncitori procesare carne (transare, ambalare)", "Operatori linii productie", "Tehnicieni mentenanta", "Personal curatenie industriala"]
            m = ["Echipamente transare", "Linii ambalare vid", "Sisteme frigorifice"]
            s = ["Recrutare personal necalificat (Nepal, Bangladesh)", "Certificare calitate"]
        else:
            w = ["Personal productie", "Operatori", "Muncitori depozit"]
            m = ["Echipamente industriale alimentare"]
            s = ["Logistica", "Distributie"]

    elif sector == "Manufacturing and Services":
        if any(x in text for x in ["aerospace", "aeronaut", "sonaca", "alloy"]):
            w = ["Operatori CNC", "Muncitori calificati composit/metal", "Tehnicieni aviatie", "Muncitori constructie fabrica greenfield"]
            m = ["Utilaje CNC", "Materiale compozite", "Aliaje speciale"]
            s = ["Certificari aviatie (EASA)", "Training specializat"]
        elif any(x in text for x in ["warehouse", "depozit", "altex"]):
            w = ["Muncitori constructie hala", "Personal depozit/logistica", "Operatori stivuitoare"]
            m = ["Structuri metalice", "Panouri sandwich", "Echipamente logistice", "Rafturi depozit"]
            s = ["Proiectare hala", "Sisteme WMS"]
        else:
            w = ["Personal operational"]
            m = []
            s = ["Consultanta"]

    elif sector == "Transport":
        if any(x in text for x in ["road", "drum", "cnair"]):
            w = ["Asfaltatori", "Operatori utilaje grele", "Muncitori drumuri", "Topografi"]
            m = ["Mixtura asfaltica", "Agregate", "Emulsie bituminoasa", "Parapeti metalici"]
            s = ["Proiectare drumuri", "Dirigentare", "Laborator incercari"]
        elif any(x in text for x in ["port", "electrif", "csct"]):
            w = ["Electricieni industriali", "Montatori", "Sudori"]
            m = ["Echipamente electrificare portuara", "Transformatoare", "Statii incarcare"]
            s = ["Proiectare electrica", "Consultanta portuara"]
        elif any(x in text for x in ["posta", "postal", "parcel"]):
            w = ["Muncitori constructie centre sortare", "Personal sortare/procesare", "IT/automatizare"]
            m = ["Echipamente sortare automata", "Benzi transportoare", "Sisteme scanare"]
            s = ["Proiectare logistica", "IT integrare"]
        else:
            w = ["Muncitori constructii", "Operatori"]
            m = ["Materiale constructii"]
            s = ["Proiectare"]

    else:
        s = ["Efect indirect - finantare IMM-uri prin banci intermediare"]

    return w, m, s

for p in projects:
    psd = p["psd_id"]
    safe_title = re.sub(r'[<>:"/\\|?*]', '', p["title"])[:60].strip().rstrip('.')
    dirname = f"{psd}_{safe_title}"
    dirpath = os.path.join(base, dirname)
    os.makedirs(dirpath, exist_ok=True)

    workers, materials, services = analyze_needs(p["sector"], p["title"], p["overview"])

    is_financial = p["sector"] in ("Financial Institutions", "Equity Funds", "Notice Type")
    priority = "INDIRECT" if is_financial else ("HIGH" if p["contact_email"] else "MEDIUM")

    workers_md = "\n".join(f"- {x}" for x in workers) if workers else "- No direct workforce needs (financial/indirect project)"
    materials_md = "\n".join(f"- {x}" for x in materials) if materials else "- No direct material needs"
    services_md = "\n".join(f"- {x}" for x in services) if services else "- N/A"

    claude = f"""# {p['title']}

## EBRD Project
- **PSD ID:** {psd}
- **Sector:** {p['sector']}
- **Status:** {p['status']}
- **EBRD Finance:** {p['finance'] or 'N/A'}
- **Total Cost:** {p['total_cost'] or 'N/A'}
- **URL:** {p['url']}
- **Priority:** {priority}

## Contact
- **Name:** {p['contact_name'] or 'N/A'}
- **Email:** {p['contact_email'] or 'N/A'}
- **Phone:** {p['contact_phone'] or 'N/A'}
- **Website:** {p['contact_website'] or 'N/A'}
- **Address:** {p['contact_address'] or 'N/A'}

## Overview
{p['overview'][:1500] if p['overview'] else 'No overview available.'}

## Needs Analysis

### Workers
{workers_md}

### Materials / Equipment
{materials_md}

### Services
{services_md}

## Sales Approach
- **Step 1:** Identify contractor/executor via SEAP (e-licitatie.ro) or direct contact
- **Step 2:** Personalized email referencing this EBRD project
- **Step 3:** Phone follow-up 48h after email
- **Step 4:** Offer with specific worker profiles / material quotes

## Status Tracking
- [ ] Contractor identified
- [ ] First contact sent
- [ ] Response received
- [ ] Meeting scheduled
- [ ] Offer sent
- [ ] Contract signed
"""
    with open(os.path.join(dirpath, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(claude)

print(f"Created {len(projects)} project directories with CLAUDE.md")
prios = Counter("INDIRECT" if p["sector"] in ("Financial Institutions", "Equity Funds", "Notice Type") else ("HIGH" if p["contact_email"] else "MEDIUM") for p in projects)
for k, v in sorted(prios.items()):
    print(f"  {k}: {v}")
