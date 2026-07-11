#!/usr/bin/env python3
"""Central config for OPENCODE TRADING ROBOT.

Two SEPARATE desks share one codebase but NOT one data model:
  - FV (fruit/vegetables): JSONL ledger in DATA/offers_ledger.jsonl + price_book.json
  - GRAIN (cultura mare: grau/porumb/orz/floarea-soarelui/rapita): PostgreSQL
    `trading_offers` (category='cereal') + `cereale_price_benchmark`.

Grain and fruit/veg trade differently (kg vs tone, wholesale vs MATIF/Constanta
FOB, fabrici vs silozuri) -> kept distinct on purpose.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "DATA")

# FV desk paths
FV_LEDGER = os.path.join(DATA, "offers_ledger.jsonl")
FV_PRICE_BOOK = os.path.join(DATA, "price_book.json")
RAW_EMAIL_DIR = os.path.join(DATA, "raw_emails")
DRAFT_DIR = os.path.join(DATA, "drafts")

# Grain desk (PostgreSQL canonical store)
DB = dict(host="127.0.0.1", port=5432, dbname="interjob_master",
          user="tudor", password="tudor")

# Inboxes (read-only)
YAHOO_INBOX = "apaminerala@yahoo.com"      # F&V + cereal suppliers
GMAIL_INBOX = "cumparlegume@gmail.com"     # COOP_EXPORT replies + cereal silozuri

# Publishing configs (gitignored; copy templates and fill)
FB_CFG = os.path.join(DATA, "fb_cumparlegume.json")
TG_CFG = os.path.join(DATA, "telegram_cumparlegume.json")
TG_CEREALE_CFG = os.path.join(DATA, "telegram_cereale.json")
WP_CFG = os.path.join(DATA, "wp_cumparlegume.json")
WHATSAPP_CFG = os.path.join(DATA, "whatsapp_internal.json")

# SILOZURI = canonical grain buyer base (PLAN 01 07 2026 root).
PLAN_ROOT = os.path.dirname(os.path.dirname(ROOT))  # .../PLAN 01 07 2026


def resolve_silozuri(*rel):
    """Resolve a path inside SILOZURI (canonical grain buyers), env-overridable."""
    env = os.environ.get("SILOZURI_DATA")
    base = env if env else os.path.join(PLAN_ROOT, "SILOZURI", "DATA")
    return os.path.join(base, *rel)


def silozuri_buyers_csv():
    """Canonical grain buyers (SILOZURI/BUYERS/cereal_buyers_romania.csv)."""
    env = os.environ.get("SILOZURI_BUYERS")
    if env:
        return env
    return os.path.join(PLAN_ROOT, "SILOZURI", "BUYERS", "cereal_buyers_romania.csv")
