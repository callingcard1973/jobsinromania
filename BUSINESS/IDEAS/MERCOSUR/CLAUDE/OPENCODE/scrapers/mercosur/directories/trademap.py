#!/usr/bin/env python3
"""TradeMap - UN ITC Trade Statistics Scraper"""

import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_trademap")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/html"
}

# Key Mercosur HS codes
HS_CODES = {
    "lithium": "283691",
    "niobium": "261590",
    "beef": "0201",
    "honey": "0409",
    "wine": "2204",
    "soy": "1201",
    "sugar": "1701",
    "coffee": "0901",
    "aluminum": "7601",
    "copper": "7403"
}

MERCOSUR_CODES = {
    "076": "Brazil",
    "032": "Argentina",
    "152": "Chile",
    "858": "Uruguay",
    "600": "Paraguay",
    "068": "Bolivia"
}

def get_trade_data(hs_code: str, reporter: str) -> dict:
    """Get trade statistics from TradeMap API"""

    # TradeMap requires authentication for full data
    # This scrapes what's publicly available
    url = f"https://www.trademap.org/Country_SelProductCountry_TS.aspx"

    params = {
        "nvpm": f"1|{reporter}|||{hs_code}|TOTAL|||2|1|1|2|2|1|1|1|1|1"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            # Parse the response for trade values
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Extract trade data from table
            data = {
                "reporter": MERCOSUR_CODES.get(reporter, reporter),
                "hs_code": hs_code,
                "exports": [],
                "imports": []
            }

            for row in soup.select('table tr[data-country]'):
                country = row.get('data-country', '')
                value = row.select_one('.value').get_text(strip=True) if row.select_one('.value') else "0"
                data["exports"].append({"country": country, "value": value})

            return data
    except Exception as e:
        print(f"Error getting trade data: {e}")

    return {}

def get_top_exporters(hs_code: str) -> list:
    """Get top exporting companies for an HS code"""
    exporters = []

    # This would require enterprise access to TradeMap
    # Fallback to UN Comtrade data
    url = "https://comtrade.un.org/api/get"

    params = {
        "type": "C",
        "freq": "A",
        "px": "HS",
        "ps": "2023",
        "r": "all",
        "p": "0",
        "rg": "2",  # Exports
        "cc": hs_code,
        "fmt": "json"
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            for record in data.get("dataset", []):
                if record.get("rtCode") in ["076", "032", "858", "600"]:  # Mercosur
                    exporters.append({
                        "country": record.get("rtTitle", ""),
                        "hs_code": hs_code,
                        "trade_value": record.get("TradeValue", 0),
                        "year": record.get("yr", 2023)
                    })
    except Exception as e:
        print(f"Comtrade error: {e}")

    return exporters

def main():
    print("=== TradeMap Statistics Scraper ===")
    all_data = {}

    for product, hs_code in HS_CODES.items():
        print(f"Getting data for {product} (HS {hs_code})")
        all_data[product] = {
            "hs_code": hs_code,
            "exporters": get_top_exporters(hs_code),
            "trade_by_country": {}
        }

        for country_code, country_name in MERCOSUR_CODES.items():
            trade = get_trade_data(hs_code, country_code)
            if trade:
                all_data[product]["trade_by_country"][country_name] = trade

        time.sleep(1)

    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = OUTPUT_DIR / f"trademap_stats_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"Saved trade data to {output_file}")
    return all_data

if __name__ == "__main__":
    main()
