#!/usr/bin/env python3
"""Test listafirme.ro lookup for a few CUIs."""
import csv
import re
import requests

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"

with open(ENRICHED, "r", encoding="utf-8") as f:
    rows = [r for r in csv.DictReader(f) if not r.get("email") and r.get("cui")]

print(f"Testing 5 CUIs from {len(rows)} without email")
headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"}

for row in rows[:5]:
    cui = row["cui"]
    url = f"https://www.listafirme.ro/{cui}/"
    r = requests.get(url, headers=headers, timeout=20)
    print(f"\nCUI {cui} ({row['winner_name'][:40]}): HTTP {r.status_code}, {len(r.text)} bytes")
    em = re.findall(r'mailto:([^"]+)', r.text)
    ph = re.findall(r'tel:([^"]+)', r.text)
    ws = re.findall(r'href="(https?://(?!(?:www\.)?listafirme|(?:www\.)?facebook|(?:www\.)?google)[^"]{5,})"[^>]*target="_blank"', r.text)
    title = re.search(r'<title>([^<]+)', r.text)
    print(f"  title: {title.group(1)[:60] if title else 'none'}")
    print(f"  mailto: {em}")
    print(f"  tel: {ph}")
    print(f"  website: {ws[:2]}")
