#!/usr/bin/env python3
"""Enrich Mercosur producers with contact data from web"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

INPUT_FILE = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_master/mercosur_all_producers_20260322.json")
OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_master")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Known company websites and contacts
KNOWN_CONTACTS = {
    # BRAZIL - Major exporters
    "jbs s.a.": {"website": "jbs.com.br", "email": "ri@jbs.com.br"},
    "marfrig global foods": {"website": "marfrig.com.br", "email": "ri@marfrig.com.br"},
    "minerva foods": {"website": "minervafoods.com", "email": "ri@minervafoods.com"},
    "brf s.a.": {"website": "bfrfoods.com", "email": "ri@bfrfoods.com"},
    "suzano": {"website": "suzano.com.br", "email": "ri@suzano.com.br"},
    "vale s.a.": {"website": "vale.com", "email": "ri@vale.com"},
    "gerdau": {"website": "gerdau.com", "email": "ri@gerdau.com.br"},
    "csn (companhia siderurgica nacional)": {"website": "csn.com.br"},
    "weg": {"website": "weg.net", "email": "ri@weg.net"},
    "embraer": {"website": "embraer.com", "email": "ri@embraer.com.br"},
    "braskem": {"website": "braskem.com.br", "email": "ri@braskem.com.br"},
    "raizen": {"website": "raizen.com.br", "email": "ri@raizen.com.br"},
    "klabin": {"website": "klabin.com.br", "email": "ri@klabin.com.br"},
    "cbmm": {"website": "cbmm.com", "email": "contato@cbmm.com.br"},
    "sigma lithium": {"website": "sigmalithium.com", "email": "info@sigmalithium.com"},
    "alpargatas": {"website": "alpargatas.com.br", "email": "ri@alpargatas.com.br"},
    "cooxupe": {"website": "cooxupe.com.br", "email": "cooxupe@cooxupe.com.br"},
    "citrosuco": {"website": "citrosuco.com.br", "email": "contato@citrosuco.com.br"},
    "bunge brasil": {"website": "bunge.com.br", "email": "faleconosco@bunge.com"},
    "cargill brasil": {"website": "cargill.com.br", "email": "brasil@cargill.com"},
    "amaggi": {"website": "amaggi.com.br", "email": "amaggi@amaggi.com.br"},
    "casa valduga": {"website": "casavalduga.com.br", "email": "valduga@casavalduga.com.br"},
    "miolo wine group": {"website": "miolo.com.br", "email": "miolo@miolo.com.br"},

    # ARGENTINA - Major exporters
    "catena zapata": {"website": "catenawines.com", "email": "info@catenawines.com"},
    "bodega catena zapata": {"website": "catenawines.com", "email": "info@catenawines.com"},
    "trapiche": {"website": "trapiche.com.ar", "email": "info@trapiche.com.ar"},
    "luigi bosca": {"website": "luigibosca.com.ar", "email": "info@luigibosca.com.ar"},
    "bodega norton": {"website": "norton.com.ar", "email": "info@norton.com.ar"},
    "achaval ferrer": {"website": "achavalferrer.com", "email": "info@achavalferrer.com"},
    "zuccardi": {"website": "familiazuccardi.com", "email": "info@familiazuccardi.com"},
    "livent argentina": {"website": "livent.com", "email": "info@livent.com"},
    "livent corporation": {"website": "livent.com", "email": "info@livent.com"},
    "allkem (olaroz)": {"website": "allkem.com", "email": "info@allkem.com"},
    "arcadium lithium": {"website": "arcadiumlithium.com", "email": "info@arcadiumlithium.com"},
    "frigorifico gorina": {"website": "gorina.com.ar", "email": "ventas@gorina.com.ar"},
    "grupo los grobo": {"website": "losgrobo.com", "email": "info@losgrobo.com"},
    "agd": {"website": "agd.com.ar", "email": "info@agd.com.ar"},
    "molinos rio de la plata": {"website": "molinosrio.com.ar"},
    "nexco": {"website": "nexco.com.ar", "email": "nexco@nexco.com.ar"},
    "nexco coop": {"website": "nexco.com.ar", "email": "nexco@nexco.com.ar"},

    # CHILE - Major exporters
    "codelco": {"website": "codelco.com", "email": "contacto@codelco.cl"},
    "antofagasta minerals": {"website": "aminerals.cl", "email": "info@aminerals.cl"},
    "sqm (sociedad quimica y minera)": {"website": "sqm.com", "email": "sqm@sqm.com"},
    "concha y toro": {"website": "conchaytoro.com", "email": "info@conchaytoro.com"},
    "santa rita": {"website": "santarita.com", "email": "info@santarita.com"},
    "undurraga": {"website": "undurraga.cl", "email": "info@undurraga.cl"},
    "mowi chile": {"website": "mowi.com", "email": "chile@mowi.com"},
    "aquachile": {"website": "aquachile.com", "email": "info@aquachile.com"},
    "blumar": {"website": "blumar.com", "email": "info@blumar.com"},
    "camanchaca": {"website": "camanchaca.cl", "email": "info@camanchaca.cl"},
    "cmpc": {"website": "cmpc.cl", "email": "info@cmpc.cl"},
    "arauco": {"website": "arauco.cl", "email": "info@arauco.cl"},
    "hortifrut": {"website": "hortifrut.com", "email": "info@hortifrut.com"},

    # URUGUAY - Major exporters
    "conaprole": {"website": "conaprole.com.uy", "email": "info@conaprole.com.uy"},
    "frigorifico tacuarembo": {"website": "tacuarembo.com.uy", "email": "info@tacuarembo.com.uy"},
    "frigorifico las piedras": {"website": "flp.com.uy", "email": "info@flp.com.uy"},
    "breeders & packers uruguay": {"website": "bpu.com.uy", "email": "info@bpu.com.uy"},
    "breeders & packers uruguay (bpu)": {"website": "bpu.com.uy", "email": "info@bpu.com.uy"},
    "saman": {"website": "saman.com.uy", "email": "info@saman.com.uy"},
    "upm uruguay": {"website": "upm.com", "email": "info.uy@upm.com"},
    "montes del plata": {"website": "montesdelplata.com.uy", "email": "info@montesdelplata.com.uy"},

    # PARAGUAY - Major exporters
    "frigorifico concepcion": {"website": "fc.com.py", "email": "info@fc.com.py"},
    "azucarera paraguaya (azpa)": {"website": "azpa.com.py", "email": "info@azpa.com.py"},
}

def enrich_producer(producer):
    """Enrich a single producer with known data"""
    name_lower = producer.get("name", "").lower().strip()

    if name_lower in KNOWN_CONTACTS:
        contact = KNOWN_CONTACTS[name_lower]
        for key, val in contact.items():
            if not producer.get(key):
                producer[key] = val
        producer["enriched"] = True

    return producer

def main():
    print("=== Contact Enrichment ===")

    # Load producers
    with open(INPUT_FILE) as f:
        producers = json.load(f)

    print(f"Loaded {len(producers)} producers")

    # Enrich from known contacts
    enriched_count = 0
    for p in producers:
        before_email = p.get("email")
        enrich_producer(p)
        if not before_email and p.get("email"):
            enriched_count += 1

    print(f"Enriched {enriched_count} new contacts from known data")

    # Count quality
    has_website = sum(1 for p in producers if p.get('website'))
    has_email = sum(1 for p in producers if p.get('email'))

    print(f"\n=== UPDATED DATA QUALITY ===")
    print(f"  With website: {has_website} ({100*has_website/len(producers):.1f}%)")
    print(f"  With email: {has_email} ({100*has_email/len(producers):.1f}%)")

    # Save enriched file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = OUTPUT_DIR / f"mercosur_producers_enriched_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(producers, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_file}")

    # Also save as CSV
    import csv
    csv_file = OUTPUT_DIR / f"mercosur_producers_enriched_{timestamp}.csv"
    fieldnames = ['name', 'country', 'sector', 'website', 'email', 'phone', 'capacity', 'source']
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for p in producers:
            writer.writerow(p)
    print(f"Saved CSV: {csv_file}")

    # Show samples with email
    print(f"\n=== SAMPLE CONTACTS ===")
    with_email = [p for p in producers if p.get('email')][:15]
    for p in with_email:
        print(f"  {p['name'][:30]:30} | {p.get('email', '')}")

    return producers

if __name__ == "__main__":
    main()
