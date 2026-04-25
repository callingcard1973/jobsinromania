"""Campaign config, template loading, and personalization."""
import os
import json
import random
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/EMAIL/.env")
load_dotenv("/opt/EMAIL/CAMPAIGNS/.env")

CAMPAIGN_DIR    = Path(__file__).parent
TEMPLATES_DIR   = CAMPAIGN_DIR / "templates"
SENDERS_FILE    = CAMPAIGN_DIR / "configs" / "senders.json"
SECTORS_FILE    = CAMPAIGN_DIR / "configs" / "sectors.json"
SIGNATURES_FILE = CAMPAIGN_DIR / "configs" / "signatures.json"

BUSINESS_HOURS_START = 8
BUSINESS_HOURS_END   = 18
BUSINESS_DAYS        = [0, 1, 2, 3, 4]


def is_business_hours():
    now = datetime.now()
    if now.weekday() not in BUSINESS_DAYS:
        return False, f"Weekend (day {now.weekday()})"
    if now.hour < BUSINESS_HOURS_START:
        return False, f"Before {BUSINESS_HOURS_START}:00"
    if now.hour >= BUSINESS_HOURS_END:
        return False, f"After {BUSINESS_HOURS_END}:00"
    return True, "OK"


def load_senders():
    return json.loads(SENDERS_FILE.read_text())


def load_sectors():
    return json.loads(SECTORS_FILE.read_text())


def load_signatures():
    return json.loads(SIGNATURES_FILE.read_text())


def get_sector_brevo(sector, senders):
    sector_map = senders.get("campaigns", {}).get("TUDOR_ANOFM", {}).get("sectors", {})
    sender_key = sector_map.get(sector or "general", "brevo:interjob")
    _, name = sender_key.split(":", 1)
    cfg = senders.get("brevo", {}).get(name, senders["brevo"]["interjob"])
    return {
        "api_key":     os.getenv(cfg["env_key"], ""),
        "email":       cfg["email"],
        "name":        cfg["name"],
        "daily_limit": cfg.get("daily_limit", 290),
    }


def get_signature(brevo_cfg, signatures):
    """Pick signature based on sender. Lucian for bppltd/lucian senders, Elena otherwise."""
    sender_email = brevo_cfg.get("email", "")
    for sig in signatures:
        for s in sig.get("senders", []):
            if s in sender_email or s in brevo_cfg.get("name", "").lower():
                return sig
    return signatures[0]


def load_template():
    lines = (TEMPLATES_DIR / "master.txt").read_text().split("\n")
    subject = lines[0].replace("Subject:", "").strip()
    body = "\n".join(lines[2:])
    return subject, body


def _sender_site(email):
    domain = email.split("@")[-1] if "@" in email else ""
    if not domain or any(x in domain for x in ("gmail.com", "yahoo", "hotmail", "outlook")):
        return ""
    return domain


ANGAJATORI_DOMAINS = {"buildjobs.eu", "factoryjobs.eu", "warehouseworkers.eu", "bppltd.co.uk"}


def _sig_block(sig, site=""):
    lines = [sig["name"], sig["title"], sig["phone"],
             "WhatsApp: https://wa.me/" + sig["whatsapp"]]
    if site:
        lines.append(site)
        if site in ANGAJATORI_DOMAINS:
            lines.append("Angajatori: https://" + site + "/angajatori/")
    return "\n".join(lines)


def personalize(template, contact, sectors=None, sig=None, site=""):
    text = template
    first_name   = (contact.get("first_name")   or "").strip()
    last_name    = (contact.get("last_name")    or "").strip()
    contact_name = (contact.get("contact_name") or "").strip()
    company      = (contact.get("company")      or "").strip()
    city_raw     = (contact.get("city")         or "").strip()
    county       = (contact.get("county")       or "").strip()
    position     = (contact.get("position")     or "").strip()
    position_first = position.split("\n")[0].strip() if position else ""
    sector       = (contact.get("sector")       or "").strip()

    city      = city_raw.split(">")[-1].strip() if ">" in city_raw else city_raw
    full_name = (first_name + " " + last_name).strip() or contact_name or ""
    greeting  = ("Buna ziua, " + full_name + ",") if full_name else "Buna ziua,"
    in_city   = (" din " + city) if city else ((" din judetul " + county) if county else "")

    email_addr   = (contact.get("email") or "").strip()
    contact_line = (", " + full_name) if full_name else ""
    tokens = {
        "{greeting}": greeting, "{for_company}": (" pentru " + company) if company else "",
        "{in_city}": in_city, "{first_name}": first_name, "{last_name}": last_name,
        "{full_name}": full_name, "{contact_name}": contact_name or full_name,
        "{company}": company, "{company_name}": company,
        "{city}": city, "{county}": county, "{position}": position,
        "{position_first}": position_first, "{sector}": sector,
        "{email}": email_addr, "{contact_line}": contact_line,
    }
    for token, val in tokens.items():
        text = text.replace(token, val)

    if sectors:
        sd = sectors.get(sector, sectors.get("general", {}))
        text = text.replace("{roles}", sd.get("roles", ""))
        text = text.replace("{sector_subject}", sd.get("subject", "Muncitori disponibili"))

    if sig:
        text = text.replace("{signature}", _sig_block(sig, site))

    text = text.replace("{unsubscribe_url}",
                        "https://interjob.ro/unsubscribe?e=" + contact.get("email", ""))
    text = re.sub(r"\{\w+\}", "", text)
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n\n\n+", "\n\n", text)
    return text
