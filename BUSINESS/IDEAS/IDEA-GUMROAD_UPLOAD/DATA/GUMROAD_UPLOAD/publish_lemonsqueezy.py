#!/usr/bin/env python3
"""Publica toate produsele pe LemonSqueezy via API."""
import json, os, requests, time

API = "https://api.lemonsqueezy.com/v1"
KEY = open(os.path.join(os.path.dirname(__file__), ".env")).read().split("=", 1)[1].strip()
STORE_ID = "344296"
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
}

PRODUCTS = [
    {"name": "Germany B2B Procurement Winners — 64,646 Companies", "price": 49900, "file": "ted_winners_DEU.csv", "records": "64,646", "country": "Germany"},
    {"name": "France B2B Procurement Winners — 62,546 Companies", "price": 49900, "file": "ted_winners_FRA.csv", "records": "62,546", "country": "France"},
    {"name": "Sweden B2B Procurement Winners — 29,409 Companies", "price": 29900, "file": "ted_winners_SWE.csv", "records": "29,409", "country": "Sweden"},
    {"name": "Poland B2B Procurement Winners — 28,209 Companies", "price": 29900, "file": "ted_winners_POL.csv", "records": "28,209", "country": "Poland"},
    {"name": "Spain B2B Procurement Winners — 25,956 Companies", "price": 29900, "file": "ted_winners_ESP.csv", "records": "25,956", "country": "Spain"},
    {"name": "Czech Republic B2B Procurement Winners — 18,406 Companies", "price": 19900, "file": "ted_winners_CZE.csv", "records": "18,406", "country": "Czech Republic"},
    {"name": "Italy B2B Procurement Winners — 16,750 Companies", "price": 19900, "file": "ted_winners_ITA.csv", "records": "16,750", "country": "Italy"},
    {"name": "Romania B2B Procurement Winners — 12,778 Companies", "price": 14900, "file": "ted_winners_ROU.csv", "records": "12,778", "country": "Romania"},
    {"name": "Finland B2B Procurement Winners — 11,694 Companies", "price": 14900, "file": "ted_winners_FIN.csv", "records": "11,694", "country": "Finland"},
    {"name": "Netherlands B2B Procurement Winners — 10,639 Companies", "price": 14900, "file": "ted_winners_NLD.csv", "records": "10,639", "country": "Netherlands"},
    {"name": "Belgium B2B Procurement Winners — 9,128 Companies", "price": 9900, "file": "ted_winners_BEL.csv", "records": "9,128", "country": "Belgium"},
    {"name": "Bulgaria B2B Procurement Winners — 8,671 Companies", "price": 9900, "file": "ted_winners_BGR.csv", "records": "8,671", "country": "Bulgaria"},
    {"name": "Austria B2B Procurement Winners — 8,262 Companies", "price": 9900, "file": "ted_winners_AUT.csv", "records": "8,262", "country": "Austria"},
    {"name": "Norway B2B Procurement Winners — 8,261 Companies", "price": 9900, "file": "ted_winners_NOR.csv", "records": "8,261", "country": "Norway"},
    {"name": "Hungary B2B Procurement Winners — 7,966 Companies", "price": 9900, "file": "ted_winners_HUN.csv", "records": "7,966", "country": "Hungary"},
    {"name": "Denmark B2B Procurement Winners — 6,568 Companies", "price": 9900, "file": "ted_winners_DNK.csv", "records": "6,568", "country": "Denmark"},
    {"name": "Ireland B2B Procurement Winners — 5,527 Companies", "price": 9900, "file": "ted_winners_IRL.csv", "records": "5,527", "country": "Ireland"},
    {"name": "UK B2B Procurement Winners — 2,901 Companies", "price": 9900, "file": "ted_winners_GBR.csv", "records": "2,901", "country": "UK"},
    {"name": "Norway Companies Full Database — 324,000 Businesses", "price": 99900, "file": "norway_companies_314K.csv", "records": "324,000", "country": "Norway"},
]

DESC_TEMPLATE = """<h2>{records} verified B2B contacts from {country}</h2>
<p>Companies that have won EU public procurement contracts, extracted from official TED (Tenders Electronic Daily) records 2020-2025.</p>
<h3>What's included (CSV format):</h3>
<ul>
<li>Company name</li>
<li>Email (verified, direct)</li>
<li>City</li>
<li>Website</li>
<li>Contract value (EUR)</li>
<li>Sector (CPV code)</li>
<li>Contracting authority</li>
<li>Year of contract</li>
</ul>
<h3>Who is this for:</h3>
<ul>
<li>B2B sales teams targeting {country}</li>
<li>Recruitment agencies seeking employers</li>
<li>Market researchers analyzing {country} procurement</li>
<li>Lead generation for {country} market entry</li>
</ul>
<h3>Data quality:</h3>
<ul>
<li>Source: Official EU procurement records (TED)</li>
<li>Period: 2020-2025</li>
<li>Format: CSV (opens in Excel, Google Sheets, any CRM)</li>
<li>Deduplicated: One row per unique company</li>
</ul>
<p><strong>These companies have WON government contracts — they are active, verified, and have budget.</strong></p>"""

NORWAY_DESC = """<h2>324,000 Norwegian companies with verified email addresses</h2>
<p>Complete extract from Norway's official Brønnøysund business register.</p>
<h3>Fields included:</h3>
<ul>
<li>Company name</li>
<li>Email</li>
<li>Phone</li>
<li>Website</li>
<li>NACE sector code + description</li>
<li>Employee count</li>
<li>City + Municipality + Postal code</li>
<li>Registration date</li>
<li>Legal form</li>
</ul>
<h3>Perfect for:</h3>
<ul>
<li>Selling to Norwegian market</li>
<li>Recruitment in Norway</li>
<li>Market research Scandinavia</li>
<li>B2B lead generation</li>
</ul>
<p>Source: Official Norwegian government register (Brønnøysundregistrene). Format: CSV, instant download.</p>"""


def create_product(product):
    """Creeaza produs pe LemonSqueezy."""
    is_norway_full = "324,000" in product["records"]
    desc = NORWAY_DESC if is_norway_full else DESC_TEMPLATE.format(**product)

    payload = {
        "data": {
            "type": "products",
            "attributes": {
                "name": product["name"],
                "description": desc,
                "price": product["price"],
                "status": "published",
                "product_type": "digital",
            },
            "relationships": {
                "store": {
                    "data": {"type": "stores", "id": STORE_ID}
                }
            }
        }
    }

    r = requests.post(f"{API}/products", headers=HEADERS, json=payload)
    return r.status_code, r.json()


def main():
    print(f"Publicare {len(PRODUCTS)} produse pe LemonSqueezy...")
    print(f"Store: {STORE_ID}\n")

    success = 0
    for i, p in enumerate(PRODUCTS, 1):
        print(f"[{i}/{len(PRODUCTS)}] {p['name'][:50]}... ", end="")
        status, data = create_product(p)
        if status in (200, 201):
            pid = data.get("data", {}).get("id", "?")
            print(f"OK (ID: {pid})")
            success += 1
        else:
            err = data.get("errors", [{}])[0].get("detail", str(data)[:100])
            print(f"EROARE {status}: {err}")
        time.sleep(1)

    print(f"\nRezultat: {success}/{len(PRODUCTS)} produse create")
    print(f"Store: https://datadrivenlemon.lemonsqueezy.com")


if __name__ == "__main__":
    main()
