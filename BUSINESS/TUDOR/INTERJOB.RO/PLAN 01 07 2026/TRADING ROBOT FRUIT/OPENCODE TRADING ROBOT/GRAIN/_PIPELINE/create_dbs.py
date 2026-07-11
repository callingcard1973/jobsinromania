#!/usr/bin/env python3
"""Creeaza grain.db + VegFru.db cu schema 50 coloane + tabele auxiliare."""
import os, sys, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(BASE, "DATA")

PARTNER_COLS = """
    firma_cui TEXT PRIMARY KEY,
    firma_nume TEXT,
    judet TEXT, oras TEXT, localitate TEXT, adresa TEXT, cod_postal TEXT, tara TEXT,
    telefon_fix TEXT, telefon_mobil TEXT, whatsapp TEXT,
    email_principal TEXT, email_alternativ TEXT,
    caen_principal TEXT, caen_secundare TEXT,
    tip_firma TEXT, inregistrare_firma TEXT,
    capital_social TEXT, cifra_afaceri TEXT, numar_angajati TEXT,
    tip_trader TEXT, tip_produs TEXT, segment TEXT,
    suprafata_agricola TEXT, suprafata_irie TEXT, suprafata_ecologica TEXT,
    capacitate_productie TEXT,
    produse_principale TEXT, produse_secundare TEXT,
    capacitate_consum TEXT, capacitate_stocare TEXT,
    depozit_licentiat TEXT, tip_depozit TEXT,
    certificari_gmp TEXT, certificari_iasc TEXT,
    umiditate_max TEXT, proteina_min TEXT, test_weight_min TEXT, admixture_max TEXT,
    calitate_certificata TEXT,
    platitor_tva TEXT, rating_financiar TEXT,
    valoare_contracte TEXT, insolventa TEXT,
    data_prima_interactiune TEXT,
    numar_dealuri_inchise TEXT, valoare_dealuri TEXT,
    rating_reliability TEXT,
    piata_principala TEXT, geo_target TEXT,
    sursa TEXT, ultima_actualizare TEXT
"""

GRAIN_TABLES = {
    "trading_partners": PARTNER_COLS,
    "trading_offers": """
        offer_id TEXT PRIMARY KEY,
        product_ro TEXT, product_en TEXT,
        quantity_kg REAL, price_per_unit REAL, currency TEXT,
        origin TEXT, delivery_terms TEXT,
        quality_class TEXT, completeness TEXT,
        from_name TEXT, from_email TEXT,
        entry_type TEXT, source TEXT,
        timestamp TEXT, context TEXT,
        category TEXT DEFAULT 'cereal'
    """,
    "cereale_benchmark": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT, market TEXT,
        price REAL, currency TEXT,
        unit TEXT, source TEXT,
        timestamp TEXT
    """,
    "cereale_spread_alerts": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id TEXT, product TEXT,
        offer_price REAL, benchmark_price REAL,
        spread REAL, spread_pct REAL,
        severity TEXT, sent TEXT,
        created_at TEXT
    """,
}

VEGFRU_TABLES = {
    "trading_partners": PARTNER_COLS,
    "offers_ledger": """
        offer_id TEXT PRIMARY KEY,
        product_ro TEXT, product_en TEXT,
        quality_class TEXT, quantity_kg REAL,
        price_per_unit REAL, currency TEXT,
        origin TEXT, delivery_terms TEXT,
        completeness TEXT, entry_type TEXT,
        source TEXT, from_name TEXT, from_email TEXT,
        timestamp TEXT, context TEXT
    """,
    "price_book": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_ro TEXT, product_en TEXT,
        quality_class TEXT, origin TEXT,
        price_min REAL, price_max REAL, price_avg REAL,
        currency TEXT, unit TEXT,
        num_offers INTEGER,
        last_updated TEXT
    """,
    "deals": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offer_id TEXT, buyer_cui TEXT,
        product TEXT, quantity_kg REAL,
        price REAL, currency TEXT,
        status TEXT, notes TEXT,
        created_at TEXT, updated_at TEXT
    """,
}


def create_db(path, tables, label):
    con = sqlite3.connect(path)
    cur = con.cursor()
    for name, schema in tables.items():
        cur.execute(f"CREATE TABLE IF NOT EXISTS {name} ({schema})")
    con.commit()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = [r[0] for r in cur.fetchall()]
    con.close()
    print(f"  {label}: {path}")
    for t in existing:
        print(f"    - {t}")


def main():
    print("=== Creare baze de date SQLite ===")
    os.makedirs(DATA, exist_ok=True)
    create_db(os.path.join(DATA, "grain.db"), GRAIN_TABLES, "grain.db")
    create_db(os.path.join(DATA, "VegFru.db"), VEGFRU_TABLES, "VegFru.db")
    return 0


if __name__ == "__main__":
    sys.exit(main())
