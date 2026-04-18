#!/usr/bin/env python3
"""Auto-send catalog PDF when email arrives at catalog@[domain]."""
import os, re, base64, requests

CATALOGS_DIR = "/opt/ACTIVE/CATALOGS"
BREVO_KEY = os.getenv("BREVO_CAREWORKERS_API_KEY", "")
SENDER_EMAIL = "office@careworkers.eu"
SENDER_NAME = "Tudor Seicarescu - InterJob Solutions"
REPLY_TO = "manpower.dristor@gmail.com"
POSTHOG_KEY = "phc_shRANXNXNAHmSgf3Y3pBHWyg3X2h7C87B8xoem3rWehi"

# catalog@domain → (specialized_pdf, general_pdf)
CATALOG_DOMAIN_MAP = {
    "factoryjobs.eu":      ("factoryjobs.eu_catalog.pdf",      "factoryjobs.eu_catalog_general.pdf"),
    "buildjobs.eu":        ("buildjobs.eu_catalog.pdf",         "buildjobs.eu_catalog_general.pdf"),
    "electricjobs.eu":     ("electricjobs.eu_catalog.pdf",      "electricjobs.eu_catalog_general.pdf"),
    "careworkers.eu":      ("careworkers.eu_catalog.pdf",       "careworkers.eu_catalog_general.pdf"),
    "farmworkers.eu":      ("farmworkers.eu_catalog.pdf",       "interjob.ro_catalog.pdf"),
    "horecaworkers.eu":    ("horecaworkers.eu_catalog.pdf",     "interjob.ro_catalog.pdf"),
    "meatworkers.eu":      ("meatworkers.eu_catalog.pdf",       "interjob.ro_catalog.pdf"),
    "mechanicjobs.eu":     ("mechanicjobs.eu_catalog.pdf",      "interjob.ro_catalog.pdf"),
    "warehouseworkers.eu": ("warehouseworkers.eu_catalog.pdf",  "interjob.ro_catalog.pdf"),
    "interjob.ro":         ("interjob.ro_catalog.pdf",          "interjob.ro_catalog.pdf"),
    "expatsinromania.org": ("expatsinromania.org_catalog.pdf",  "expatsinromania.org_catalog_general.pdf"),
    "nepalezi.com":        ("nepalezi.com_catalog.pdf",         "nepalezi.com_catalog_general.pdf"),
    "mivromania.info":     ("mivromania.info_catalog.pdf",      "interjob.ro_catalog.pdf"),
    "aluminumrecyclehub.com": ("aluminumrecyclehub.com_catalog.pdf", "interjob.ro_catalog.pdf"),
    "bppltd.co.uk":        ("bppltd.co.uk_catalog.pdf",         "bppltd.co.uk_catalog_general.pdf"),
    "horecaworkers2026.eu":("horecaworkers.eu_catalog.pdf",     "horecaworkers2026.eu_catalog_general.pdf"),
}

EMAIL_BODY = """Buna ziua,

Multumesc pentru interesul acordat.

Va trimit catalogul nostru cu candidati disponibili pentru plasare imediata.
Catalogul contine profiluri verificate, cu experienta in domeniu, disponibili pentru angajare in Europa.

Atasati veti gasi:
1. Catalog specializat pe sectorul dumneavoastra
2. Catalog general cu candidati din toate domeniile

Pentru CV complet sau pentru a discuta detalii, raspundeti la acest email.

Cu stima,
Tudor Seicarescu
InterJob Solutions Europe
manpower.dristor@gmail.com
WhatsApp: +33 7 51 17 13 56
www.interjob.ro"""

def detect_catalog_domain(msg):
    """Check To/Delivered-To/X-Original-To headers for catalog@ address."""
    for header in ("To", "Delivered-To", "X-Original-To", "X-Forwarded-To"):
        val = msg.get(header, "")
        m = re.search(r'catalog@([\w.\-]+)', val, re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return None

def _send_brevo(to_email, subject, body, pdf_paths):
    attachments = []
    for path in pdf_paths:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            attachments.append({
                "content": base64.b64encode(f.read()).decode(),
                "name": os.path.basename(path),
            })
    if not attachments:
        return False, "no PDFs found"
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": SENDER_NAME},
        "to": [{"email": to_email}],
        "replyTo": {"email": REPLY_TO},
        "subject": subject,
        "textContent": body,
        "attachment": attachments,
    }
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    return r.status_code in (200, 201), r.text[:200]

def _ph_event(to_email, domain):
    try:
        requests.post("https://us.i.posthog.com/capture/", json={
            "api_key": POSTHOG_KEY,
            "event": "catalog_sent",
            "distinct_id": to_email,
            "properties": {"email": to_email, "sector": domain, "funnel_stage": "catalog_auto"},
        }, timeout=5)
    except Exception:
        pass

def handle_catalog_request(msg, sender_email, log_fn):
    """Call from response_tracker.check_inbox. Returns True if handled."""
    domain = detect_catalog_domain(msg)
    if not domain:
        return False

    pdfs = CATALOG_DOMAIN_MAP.get(domain)
    if not pdfs:
        # Unknown domain — send general interjob catalog
        pdfs = ("interjob.ro_catalog.pdf", "interjob.ro_catalog.pdf")

    pdf_paths = list({os.path.join(CATALOGS_DIR, p) for p in pdfs})
    subject = "Catalog candidati disponibili - InterJob Solutions"
    ok, msg_txt = _send_brevo(sender_email, subject, EMAIL_BODY, pdf_paths)

    if ok:
        _ph_event(sender_email, domain)
        log_fn(f"catalog_autoresponder: sent to {sender_email} [{domain}] ({len(pdf_paths)} PDFs)")
    else:
        log_fn(f"catalog_autoresponder: FAIL {sender_email} [{domain}] — {msg_txt}")

    return True
