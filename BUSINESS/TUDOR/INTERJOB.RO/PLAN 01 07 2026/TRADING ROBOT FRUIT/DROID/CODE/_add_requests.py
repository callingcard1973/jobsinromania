#!/usr/bin/env python3
import json, os

LEDGER = os.path.join(os.path.dirname(__file__), "..", "DATA", "offers_ledger.jsonl")

requests = [
    {
        "source_email_id": "legumefructe-buzau-visine",
        "from_name": "LEGUME FRUCTE BUZAU / George Doloiu",
        "from_email": "office@legumefructe-buzau.ro",
        "subject": "Cerere oferta visine 100to industrial",
        "product_ro": "visine",
        "product_en": "sour cherries",
        "quality": "industrial",
        "price": None,
        "price_currency": "RON",
        "quantity_kg": 100000,
        "origin": "Buzau",
        "completeness": "complete",
        "notes": "Cerere oferta pentru visine procesare industriala. Specs: fructe sanatoase, calibrul 18-20mm, fara fermentatie.",
        "entry_type": "request",
        "timestamp": "2026-06-25"
    },
    {
        "source_email_id": "mibprodcom-gogosari",
        "from_name": "MIB PROD COM / Marcela Stoicovici",
        "from_email": "office@mibprodcom.ro",
        "subject": "Cerere oferta gogosari 100to",
        "product_ro": "gogosari",
        "product_en": "round peppers",
        "quality": "industrial",
        "price": None,
        "price_currency": "RON",
        "quantity_kg": 100000,
        "origin": "Alba",
        "completeness": "complete",
        "notes": "Cerere oferta gogosari 100to.",
        "entry_type": "request",
        "timestamp": "2026-06-25"
    },
    {
        "source_email_id": "mibprodcom-ardei_kapia",
        "from_name": "MIB PROD COM / Marcela Stoicovici",
        "from_email": "office@mibprodcom.ro",
        "subject": "Cerere oferta ardei kapia 100to",
        "product_ro": "ardei kapia",
        "product_en": "kapia peppers",
        "quality": "industrial",
        "price": None,
        "price_currency": "RON",
        "quantity_kg": 100000,
        "origin": "Alba",
        "completeness": "complete",
        "notes": "Cerere oferta ardei kapia 100to.",
        "entry_type": "request",
        "timestamp": "2026-06-25"
    },
    {
        "source_email_id": "mibprodcom-vinete",
        "from_name": "MIB PROD COM / Marcela Stoicovici",
        "from_email": "office@mibprodcom.ro",
        "subject": "Cerere oferta vinete 60to",
        "product_ro": "vinete",
        "product_en": "eggplants",
        "quality": "industrial",
        "price": None,
        "price_currency": "RON",
        "quantity_kg": 60000,
        "origin": "Alba",
        "completeness": "complete",
        "notes": "Cerere oferta vinete 60to.",
        "entry_type": "request",
        "timestamp": "2026-06-25"
    }
]

for r in requests:
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Adaugat: {r['source_email_id']}")
