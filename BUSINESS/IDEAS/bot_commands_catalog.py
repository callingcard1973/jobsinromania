#!/usr/bin/env python3
"""Send catalog PDF to employer via Brevo. /send_catalog email sector"""
import os, requests
from telegram import Update
from telegram.ext import ContextTypes

CATALOGS_DIR = "/opt/ACTIVE/CATALOGS"
BREVO_KEY = os.getenv("BREVO_CAREWORKERS_API_KEY", "")
SENDER_EMAIL = "office@careworkers.eu"
SENDER_NAME = "Tudor Seicarescu - InterJob Solutions"
REPLY_TO = "manpower.dristor@gmail.com"

CATALOG_MAP = {
    "factory":      "factoryjobs.eu_catalog.pdf",
    "construction": "buildjobs.eu_catalog.pdf",
    "horeca":       "horecaworkers.eu_catalog.pdf",
    "care":         "careworkers.eu_catalog.pdf",
    "farm":         "farmworkers.eu_catalog.pdf",
    "electric":     "electricjobs.eu_catalog.pdf",
    "warehouse":    "warehouseworkers.eu_catalog.pdf",
    "mechanic":     "mechanicjobs.eu_catalog.pdf",
    "meat":         "meatworkers.eu_catalog.pdf",
    "expats":       "expatsinromania.org_catalog.pdf",
    "nepalezi":     "nepalezi.com_catalog.pdf",
    "mivromania":   "mivromania.info_catalog.pdf",
    "aluminum":     "aluminumrecyclehub.com_catalog.pdf",
    "bppltd":       "bppltd.co.uk_catalog.pdf",
    "general":      "catalog_general.pdf",
    "interjob":     "interjob.ro_catalog.pdf",
    # General (all-sector) variants per sender
    "factory_general":      "factoryjobs.eu_catalog_general.pdf",
    "electric_general":     "electricjobs.eu_catalog_general.pdf",
    "care_general":         "careworkers.eu_catalog_general.pdf",
    "expats_general":       "expatsinromania.org_catalog_general.pdf",
    "horeca26_general":     "horecaworkers2026.eu_catalog_general.pdf",
    "nepalezi_general":     "nepalezi.com_catalog_general.pdf",
    "bppltd_general":       "bppltd.co.uk_catalog_general.pdf",
}

EMAIL_BODY = """Bună ziua,

Mulțumesc pentru răspunsul dumneavoastră. Conform discuției, vă trimit catalogul nostru cu candidați disponibili pentru plasare imediată.

Candidații sunt verificați, disponibili pentru angajare în Europa, cu experiență în domeniu.

Pentru detalii suplimentare sau pentru a programa o discuție, vă rog să îmi răspundeți la acest email.

Cu stimă,
Tudor Seicarescu
InterJob Solutions Europe
manpower.dristor@gmail.com"""

def _send_brevo(to_email, subject, body, pdf_path):
    import base64
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    pdf_name = os.path.basename(pdf_path)
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": SENDER_NAME},
        "to": [{"email": to_email}],
        "replyTo": {"email": REPLY_TO},
        "subject": subject,
        "textContent": body,
        "attachment": [{"content": pdf_b64, "name": pdf_name}],
    }
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    return r.status_code in (200, 201), r.text[:200]

def _ph_event(email, sector):
    try:
        requests.post("https://us.i.posthog.com/capture/", json={
            "api_key": "phc_shRANXNXNAHmSgf3Y3pBHWyg3X2h7C87B8xoem3rWehi",
            "event": "catalog_sent",
            "distinct_id": email,
            "properties": {"email": email, "sector": sector, "funnel_stage": "catalog_sent"},
        }, timeout=5)
    except Exception:
        pass

async def cmd_send_catalog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/send_catalog email@x.com [sector] — send PDF catalog to employer."""
    if not ctx.args:
        opts = " | ".join(CATALOG_MAP.keys())
        await update.message.reply_text(f"Usage: /send_catalog email@x.com [sector]\nSectors: {opts}")
        return

    to_email = ctx.args[0].lower()
    sector = ctx.args[1].lower() if len(ctx.args) > 1 else "general"

    if sector not in CATALOG_MAP:
        await update.message.reply_text(f"Unknown sector. Options: {' | '.join(CATALOG_MAP.keys())}")
        return

    pdf_path = os.path.join(CATALOGS_DIR, CATALOG_MAP[sector])
    if not os.path.exists(pdf_path):
        await update.message.reply_text(f"PDF not found: {pdf_path}")
        return

    subject = f"Candidați disponibili pentru angajare - InterJob Solutions"
    await update.message.reply_text(f"Trimit catalog [{sector}] la {to_email}...")

    ok, msg = _send_brevo(to_email, subject, EMAIL_BODY, pdf_path)
    if ok:
        _ph_event(to_email, sector)
        await update.message.reply_text(f"✓ Trimis la {to_email} [{sector}]")
    else:
        await update.message.reply_text(f"FAIL: {msg}")
