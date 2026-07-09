#!/usr/bin/env python3
"""drain_terenuri.py — Drain MADR + Harghita land listings into terenuri_listings.

Reads madr_terenuri (10,129), enriches/scores, upserts into terenuri_listings.
harghita_lmv_listings noted as non-land data — logged, skipped.

Usage:
  python3 drain_terenuri.py
  python3 drain_terenuri.py --dry-run
  python3 drain_terenuri.py --source madr
"""
import logging, sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/ACTIVE/TERENURI/drain_terenuri.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("drain")

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    log.error("pip install psycopg2-binary")
    sys.exit(1)

DB = {"host": "127.0.0.1", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}
EUR_RON = 4.975  # 2026 approximate rate

# Market benchmarks for scoring — avg price/ha per category (RON)
CATEGORY_BENCHMARKS = {
    "ARABIL": 201300, "FANEATA": 184188, "LIVEZI": 175809,
    "PASUNI": 114590, "PAJISTI PERMANENTE": 166798,
    "VII": 81314, "ALTE CULTURI": 330905,
    "PEPINIERE POMICOLE": 25047,
}

# County quality score (based on avg price/ha as proxy for demand)
COUNTY_SCORES = {
    "CLUJ": 100, "BRASOV": 95, "ILFOV": 95, "BISTRITA-NASAUD": 90,
    "SIBIU": 88, "TIMIS": 85, "ARGES": 85, "IALOMITA": 82,
    "COVASNA": 80, "BACAU": 78, "SUCEAVA": 75, "PRAHOVA": 73,
    "HARGHITA": 72, "VALCEA": 70, "SALAJ": 70, "NEAMT": 70,
    "ALBA": 68, "SATU MARE": 65, "CONSTANTA": 65, "HUNEDOARA": 62,
    "DAMBOVITA": 62, "MARAMURES": 60, "BIHOR": 60, "VASLUI": 55,
    "CARAS-SEVERIN": 55, "ARAD": 52, "BUZAU": 50, "BRAILA": 50,
    "GALATI": 48, "TULCEA": 45, "TELEORMAN": 42, "VRANCEA": 40,
    "IASI": 58, "GORJ": 55, "OLT": 45, "GIURGIU": 50,
}

MADR_CATEGORY_MAP = {
    "ARABIL": "Arabil", "FANEATA": "Fâneață", "PASUNI": "Pășune",
    "VII": "Vie", "LIVEZI": "Livadă", "ALTE CULTURI": "Alte culturi",
    "PAJISTI PERMANENTE": "Pajiște permanentă",
    "PEPINIERE POMICOLE": "Pepinieră pomicolă",
}
