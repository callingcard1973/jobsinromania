#!/usr/bin/env python3
"""Parse RNPM Excel + cross-reference CSVs. Pure parsing, no DB."""
import csv
import os
import re
import unicodedata

# -- Category normalization: 12 diacritics variants -> 8 canonical ASCII forms
CATEGORY_NORM = {
    "LAPTE ŞI PRODUSE DIN LAPTE": "LAPTE SI PRODUSE DIN LAPTE",
    "LAPTE ȘI PRODUSE DIN LAPTE": "LAPTE SI PRODUSE DIN LAPTE",
    "LAPTE SI PRODUSE DIN LAPTE": "LAPTE SI PRODUSE DIN LAPTE",
    "CARNE ȘI PRODUSE DIN CARNE": "CARNE SI PRODUSE DIN CARNE",
    "CARNE ŞI PRODUSE DIN CARNE": "CARNE SI PRODUSE DIN CARNE",
    "PÂINE, PRODUSE DE PANIFICAȚIE ȘI PATISERIE": "PAINE, PRODUSE DE PANIFICATIE SI PATISERIE",
    "PAINE, PRODUSE DE PANIFICAȚIE ȘI PATISERIE": "PAINE, PRODUSE DE PANIFICATIE SI PATISERIE",
    "PEȘTE ȘI PRODUSE DIN PEȘTE": "PESTE SI PRODUSE DIN PESTE",
    "PRODUSE DIN PEȘTE": "PESTE SI PRODUSE DIN PESTE",
    "OUĂ": "OUA",
    "LEGUME -FRUCTE": "LEGUME-FRUCTE",
    "PRODUSE VEGETALE": "PRODUSE VEGETALE",
    "PRODUSE APICOLE": "PRODUSE APICOLE",
    "LEGUME-FRUCTE": "LEGUME-FRUCTE",
}


def normalize_category(cat):
    if not cat:
        return ""
    cat = cat.strip()
    return CATEGORY_NORM.get(cat, cat.upper())


def to_ascii(text):
    """Transliterate diacritics to ASCII (ă->a, ș->s, ț->t, etc.)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii")


def extract_emails(text):
    """Extract all emails, transliterate diacritics to ASCII."""
    if not text:
        return []
    found = re.findall(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", text)
    result = []
    for e in found:
        ascii_e = to_ascii(e).lower()
        if ascii_e and "@" in ascii_e:
            result.append(ascii_e)
    return result


def extract_phones(text):
    """Extract phones: 0xxx, +40xxx, and bare 9-digit formats."""
    if not text:
        return []
    phones = []
    # Match +40 format
    for m in re.findall(r"\+40\s?(\d{2,3})[\s.\-]?(\d{3})[\s.\-]?(\d{3,4})", text):
        phones.append("0" + "".join(m))
    # Match 0xxx format
    for m in re.findall(r"0(\d{2,3})[\s.\-]?(\d{3})[\s.\-]?(\d{3,4})", text):
        phones.append("0" + "".join(m))
    # Bare 9-digit (7xx xxx xxx) — prepend 0
    for m in re.findall(r"(?<!\d)([2-9]\d{2})[\s.\-]?(\d{3})[\s.\-]?(\d{3})(?!\d)", text):
        phones.append("0" + "".join(m))
    return list(dict.fromkeys(phones))  # dedup preserving order


def parse_xlsx(path):
    """Parse RNPM Excel. Returns dict of producers with per-product categories."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["RNPM"]

    producers = {}
    cur = {"year": "", "county": "", "category": "", "producer": "",
           "addr_pl": "", "addr_sed": "", "siruta": "", "decision": "",
           "contact": "", "obs": "", "is_trad": False, "has_qr": False}

    for row in ws.iter_rows(min_row=7, max_col=14, values_only=True):
        vals = (row + (None,) * 14)[:14]
        c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14 = vals

        if c1:
            cur["year"] = str(c1).strip()
        if c2:
            cur["county"] = str(c2).strip()
        if c3:
            cur["category"] = normalize_category(str(c3))
        if c5:
            cur["addr_pl"] = str(c5).strip()
        if c6:
            cur["addr_sed"] = str(c6).strip()
        if c8:
            cur["siruta"] = str(c8).strip()
        if c9:
            cur["producer"] = str(c9).strip()
            cur["is_trad"] = bool(c7)
            cur["has_qr"] = bool(c14)
        if c10:
            cur["decision"] = str(c10).strip()
        if c12:
            cur["contact"] = str(c12).strip()
        if c13:
            cur["obs"] = str(c13).strip()
        elif c9:
            cur["obs"] = ""

        product = str(c4).strip() if c4 else ""
        rnpm_nr = str(c11).strip() if c11 else ""
        if not product:
            continue

        name = cur["producer"]
        if name not in producers:
            producers[name] = {
                "name": name, "year": cur["year"], "county": cur["county"],
                "addr_pl": cur["addr_pl"], "addr_sed": cur["addr_sed"],
                "siruta": cur["siruta"], "decision": cur["decision"],
                "contact": cur["contact"], "obs": cur["obs"],
                "is_trad": cur["is_trad"], "has_qr": cur["has_qr"],
                "products": [], "product_categories": [], "rnpm_numbers": [],
                "categories": set(),
            }
        p = producers[name]
        p["products"].append(product)
        p["product_categories"].append(cur["category"])  # per-product category
        p["categories"].add(cur["category"])
        if rnpm_nr:
            p["rnpm_numbers"].append(rnpm_nr)

    wb.close()
    return producers


# -- Cross-reference CSV loaders --
def load_producatori_csv(data_dir):
    """680 email+URL pairs from website scrape."""
    path = os.path.join(data_dir, "PRODUS MONTAN PRODUCATORI.csv")
    if not os.path.exists(path):
        return {}
    data = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and "@" in row[0]:
                data[row[0].strip().lower()] = row[1].strip()
    return data


def load_email_csv(data_dir):
    """666 emails extracted from RNPM."""
    path = os.path.join(data_dir, "DATE EXTRASE", "rnpm email.csv")
    if not os.path.exists(path):
        return set()
    emails = set()
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            for cell in row:
                for part in cell.split(";"):
                    part = part.strip()
                    if "@" in part:
                        emails.add(to_ascii(part).lower())
    return emails


# -- AGRIP product classification (Annex I TFEU sectors) --
_RE_PROC_FV = re.compile(r"dulceata|gem\b|sirop|suc\b|must\b|otet|compot|conserv|murat|zacusc|magiun|sos\b|pasta\b|bulion|peleu|marmelad", re.I)
_RE_HERBS = re.compile(r"ceai|plante|salvie|roinis|menta|cimbru|tinctur|catina|sunator|soc\b|musetel|urzic|lavand|oregano|rozmarin|iarba", re.I)
_RE_CEREALS = re.compile(r"grau|porumb|secara|ovaz|orz\b|cereale|hrisca|faina\b|malai", re.I)
_RE_MATURED = re.compile(r"maturat|burduf|afumat|pastrama|slanina|uscat|salamur|presur|cabana|traditi|invechit", re.I)
_RE_PROCESSED = re.compile(r"dulceata|gem\b|sirop|carnati|carnat\b|suc\b|conserv|murat|ceai|toba\b|caltabos|lebar|salam|cremvur|parizer|pate\b|compot|zacusc|magiun|sos\b|bulion|marmelad|otet|must\b", re.I)
_RE_FRESH = re.compile(r"lapte crud|proaspat|cartofi|mere\b|rosii|ceapa|castrave|prune\b|cirese|visine|zmeura|afine\b|capsun|pepeni|oua\b|ou\b", re.I)
_RE_NON_PERISH = re.compile(r"miere|polen|propolis|ceara|pastura|fagure|laptisor", re.I)


def classify_product(product_name, rnpm_category):
    """Classify product into AGRIP sector + processing state."""
    name = to_ascii(product_name).lower() if product_name else ""
    cat = (rnpm_category or "").upper()

    # -- agrip_sector (first match wins) --
    if "APICOL" in cat:
        sector = "HONEY"
    elif "CARNE" in cat:
        sector = "MEAT"
    elif "PESTE" in cat:
        sector = "FISH"
    elif "OUA" in cat:
        sector = "DAIRY"
    elif "PAINE" in cat:
        sector = "BAKERY"
    elif "LAPTE" in cat:
        sector = "DAIRY"
    elif "VEGETALE" in cat or "LEGUME" in cat:
        if _RE_PROC_FV.search(name):
            sector = "PROCESSED_FV"
        elif _RE_HERBS.search(name):
            sector = "HERBS"
        elif _RE_CEREALS.search(name):
            sector = "CEREALS"
        else:
            sector = "FRESH_FV"
    else:
        sector = "OTHER"

    # -- processing state --
    if _RE_NON_PERISH.search(name):
        proc = "NON_PERISHABLE"
    elif _RE_MATURED.search(name):
        proc = "MATURED"
    elif _RE_PROCESSED.search(name):
        proc = "PROCESSED"
    elif _RE_FRESH.search(name):
        proc = "FRESH"
    else:
        # Default by sector
        defaults = {"HONEY": "NON_PERISHABLE", "MEAT": "FRESH",
                     "FISH": "FRESH", "DAIRY": "FRESH",
                     "BAKERY": "PROCESSED", "HERBS": "NON_PERISHABLE"}
        proc = defaults.get(sector, "FRESH")

    return sector, proc


def load_phone_csv(data_dir):
    """651 phone numbers from RNPM extraction."""
    path = os.path.join(data_dir, "DATE EXTRASE",
                        "contact rnpm doar telefon  - Sheet1.csv")
    if not os.path.exists(path):
        return set()
    phones = set()
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            for cell in row:
                cell = cell.strip().replace("/", "").replace(" ", "")
                # +40 format -> normalize to 0xxx
                m = re.match(r"\+40(\d{8,9})$", cell)
                if m:
                    phones.add("0" + m.group(1))
                    continue
                m = re.match(r"0(\d{8,9})$", cell)
                if m:
                    phones.add(cell)
    return phones
