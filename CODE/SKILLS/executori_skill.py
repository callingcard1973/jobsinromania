#!/usr/bin/env python3
"""
Executori Judecătorești Skill
Downloads and manages the full list of Romanian judicial executors
from the official API at executori.ro

Data: 836+ entries with name, CEJ, phone, email, address
Source: https://www.executori.ro/api/publicV2/tablou
"""

import requests
import json
import csv
import re
import os
import unicodedata

API_URL = "https://www.executori.ro/api/publicV2/tablou"
DATA_DIR = "/opt/DATA_IMPORT/EXECUTORI"


def normalize_phone(num):
    if not num:
        return ""
    return re.sub(r"[^\d+]", "", str(num))


def format_phone(phones):
    if not phones:
        return ""
    return ";".join(normalize_phone(p.get("numar", "")) for p in phones if isinstance(p, dict))


def format_email(emails):
    if not emails:
        return ""
    return ";".join(e.get("adresa", "") for e in emails if isinstance(e, dict))


def format_address(org):
    if not org:
        return ""
    parts = []
    for key in ["localitate", "tip_strada", "denumire_strada", "numar",
                "bl", "scara", "etaj", "apartament", "cod_postal"]:
        v = org.get(key)
        if v:
            parts.append(str(v))
    return ", ".join(parts)


def to_ascii(s):
    if s is None:
        return ""
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')


def download_executori(output_dir=None):
    """Download full executori list from API, save JSON + CSV"""
    if output_dir is None:
        output_dir = DATA_DIR
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading from {API_URL}...")
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    print(f"Received {len(data)} executors")

    # Save JSON
    json_path = os.path.join(output_dir, "executors.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {json_path}")

    # Save CSV
    csv_fields = ["unique_id", "nume", "prenume", "cej", "circumscriptie",
                  "stare", "telefon", "email", "address"]
    csv_path = os.path.join(output_dir, "executors.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for entry in data:
            writer.writerow({
                "unique_id": to_ascii(entry.get("unique_id", "")),
                "nume": to_ascii(entry.get("nume", "")),
                "prenume": to_ascii(entry.get("prenume", "")),
                "cej": to_ascii(entry.get("cej", "")),
                "circumscriptie": to_ascii(entry.get("circumscriptie", "")),
                "stare": to_ascii(entry.get("stare", "")),
                "telefon": to_ascii(format_phone(entry.get("telefon", []))),
                "email": to_ascii(format_email(entry.get("email", []))),
                "address": to_ascii(format_address(entry.get("organizatie", {}))),
            })
    print(f"Saved {csv_path}")
    return len(data)


def get_stats():
    """Return quick stats about the executori dataset"""
    csv_path = os.path.join(DATA_DIR, "executors.csv")
    if not os.path.exists(csv_path):
        return "No data found. Run download_executori() first."
    with open(csv_path, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    total = len(reader)
    with_email = sum(1 for r in reader if r.get("email"))
    with_phone = sum(1 for r in reader if r.get("telefon"))
    active = sum(1 for r in reader if r.get("stare", "").lower() == "activ")
    counties = len(set(r.get("circumscriptie", "") for r in reader if r.get("circumscriptie")))
    return {
        "total": total,
        "with_email": with_email,
        "with_phone": with_phone,
        "active": active,
        "counties": counties,
        "email_rate": f"{with_email/total*100:.0f}%" if total else "0%"
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        print(json.dumps(get_stats(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "--download":
        download_executori()
    else:
        print("Usage: executori_skill.py [--download|--stats]")
        stats = get_stats()
        if isinstance(stats, dict):
            print(json.dumps(stats, indent=2))
        else:
            print(stats)
