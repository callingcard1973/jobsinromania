#!/usr/bin/env python3
"""Generate WooCommerce product import CSV from produs_montan PostgreSQL."""
import csv
import os
import sys
import re
import psycopg2

# --
DB = dict(host="192.168.100.21", port=5432, dbname="interjob_master",
          user="tudor", password="tudor")
OUT = os.path.join(os.path.dirname(__file__), "woo_products.csv")

CAT_NORM = {
    "LAPTE ŞI PRODUSE DIN LAPTE": "Lapte si Produse Lactate",
    "LAPTE ȘI PRODUSE DIN LAPTE": "Lapte si Produse Lactate",
    "LAPTE SI PRODUSE DIN LAPTE": "Lapte si Produse Lactate",
    "PRODUSE VEGETALE": "Produse Vegetale",
    "PRODUSE APICOLE": "Produse Apicole",
    "CARNE ȘI PRODUSE DIN CARNE": "Carne si Produse din Carne",
    "CARNE ŞI PRODUSE DIN CARNE": "Carne si Produse din Carne",
    "OUĂ": "Oua",
    "PEȘTE ȘI PRODUSE DIN PEȘTE": "Peste si Produse din Peste",
    "PRODUSE DIN PEȘTE": "Peste si Produse din Peste",
    "PÂINE, PRODUSE DE PANIFICAȚIE ȘI PATISERIE": "Paine si Patiserie",
    "PAINE, PRODUSE DE PANIFICAȚIE ȘI PATISERIE": "Paine si Patiserie",
    "LEGUME -FRUCTE": "Produse Vegetale",
}


def norm_cat(c):
    return CAT_NORM.get(c, c)


def make_sku(producer_name, product_name, pid, prd_id):
    """Generate unique SKU from producer + product."""
    name_part = re.sub(r'[^a-z0-9]', '', producer_name.lower()[:10])
    prod_part = re.sub(r'[^a-z0-9]', '', product_name.lower()[:10])
    return f"PM-{name_part}-{prod_part}-{prd_id}"


def make_description(producer, county, addr, year, obs, url):
    """Build product description with producer info."""
    parts = [f"Producator certificat Produs Montan: {producer}"]
    if county:
        parts.append(f"Judet: {county}")
    if addr:
        parts.append(f"Locatie: {addr}")
    if year:
        parts.append(f"Inregistrat RNPM: {year}")
    if url:
        parts.append(f'<a href="{url}" target="_blank">Vezi pe produsmontan.ro</a>')
    if obs:
        parts.append(f"Obs: {obs}")
    parts.append("")
    parts.append("Certificat de Ministerul Agriculturii (MADR).")
    parts.append("Distribuit prin Gospodarii de Altadata Cooperativa Agricola.")
    return "\n".join(parts)


def fetch_data():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT pr.id as prd_id, pr.product_name, pr.category, pr.rnpm_number,
               p.id as pid, p.name, p.county, p.addr_sediu, p.year_registered,
               p.obs, p.website_url
        FROM produs_montan_products pr
        JOIN produs_montan_producers p ON pr.producer_id = p.id
        ORDER BY pr.category, p.name, pr.product_name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    print("Fetching products from PostgreSQL...")
    rows = fetch_data()
    print(f"  {len(rows)} products loaded")

    # WooCommerce CSV columns
    headers = [
        "Type", "SKU", "Name", "Published", "Is featured?",
        "Visibility in catalog", "Short description", "Description",
        "Tax status", "In stock?", "Stock", "Categories", "Tags",
        "Allow customer reviews?", "Sale price", "Regular price",
        "Weight (kg)", "Attribute 1 name", "Attribute 1 value(s)",
        "Attribute 2 name", "Attribute 2 value(s)",
        "Attribute 3 name", "Attribute 3 value(s)",
        "Attribute 4 name", "Attribute 4 value(s)",
    ]

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)

        for row in rows:
            prd_id, product_name, category, rnpm_num, pid, name, county, addr, year, obs, url = row
            cat = norm_cat(category) if category else "Necategorizat"
            sku = make_sku(name, product_name, pid, prd_id)
            short_desc = f"{product_name} - Produs Montan certificat din {county or 'Romania'}"
            desc = make_description(name, county, addr, year, obs, url)

            # Tags: county + producer type
            tags = []
            if county:
                tags.append(county.title())
            tags.append("Produs Montan")
            if rnpm_num:
                tags.append(f"RNPM {rnpm_num}")

            w.writerow([
                "simple",              # Type
                sku,                   # SKU
                f"{product_name} - {name}",  # Name (product + producer)
                1,                     # Published
                0,                     # Is featured
                "visible",             # Visibility
                short_desc,            # Short description
                desc,                  # Description
                "taxable",             # Tax status
                1,                     # In stock
                "",                    # Stock (empty = unlimited)
                f"Produs Montan > {cat}",  # Categories (hierarchical)
                ", ".join(tags),       # Tags
                1,                     # Allow reviews
                "",                    # Sale price (TBD)
                "",                    # Regular price (TBD — producers must confirm)
                "",                    # Weight
                "Producator",          # Attr 1 name
                name,                  # Attr 1 value
                "Judet",               # Attr 2 name
                county or "",          # Attr 2 value
                "Certificare",         # Attr 3 name
                f"RNPM {rnpm_num}" if rnpm_num else "Produs Montan",
                "An inregistrare",     # Attr 4 name
                year or "",            # Attr 4 value
            ])

    print(f"WooCommerce CSV written: {OUT}")
    print(f"  {len(rows)} products ready for import")
    print(f"  Import: WooCommerce > Products > Import > Upload CSV")
    print(f"  NOTE: Prices are empty — producers must confirm pricing first")


if __name__ == "__main__":
    main()
