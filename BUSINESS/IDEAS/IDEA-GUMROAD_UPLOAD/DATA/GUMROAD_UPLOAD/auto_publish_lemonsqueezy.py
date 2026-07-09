#!/usr/bin/env python3
"""
Publica automat 19 produse pe LemonSqueezy via Playwright (browser automation).
Ruleaza pe laptop. Deschide browser, logheaza-te manual prima data, apoi scriptul creeaza produsele.

Folosire:
  python auto_publish_lemonsqueezy.py           # toate produsele
  python auto_publish_lemonsqueezy.py --start 5  # de la produsul 5
"""
import argparse, os, sys, time
from pathlib import Path

UPLOAD_DIR = Path(__file__).parent

PRODUCTS = [
    {"name": "Germany B2B Procurement Winners — 64,646 Companies", "price": "499", "file": "ted_winners_DEU.csv", "records": "64,646", "country": "Germany"},
    {"name": "France B2B Procurement Winners — 62,546 Companies", "price": "499", "file": "ted_winners_FRA.csv", "records": "62,546", "country": "France"},
    {"name": "Sweden B2B Procurement Winners — 29,409 Companies", "price": "299", "file": "ted_winners_SWE.csv", "records": "29,409", "country": "Sweden"},
    {"name": "Poland B2B Procurement Winners — 28,209 Companies", "price": "299", "file": "ted_winners_POL.csv", "records": "28,209", "country": "Poland"},
    {"name": "Spain B2B Procurement Winners — 25,956 Companies", "price": "299", "file": "ted_winners_ESP.csv", "records": "25,956", "country": "Spain"},
    {"name": "Czech Republic B2B Procurement Winners — 18,406 Companies", "price": "199", "file": "ted_winners_CZE.csv", "records": "18,406", "country": "Czech Republic"},
    {"name": "Italy B2B Procurement Winners — 16,750 Companies", "price": "199", "file": "ted_winners_ITA.csv", "records": "16,750", "country": "Italy"},
    {"name": "Romania B2B Procurement Winners — 12,778 Companies", "price": "149", "file": "ted_winners_ROU.csv", "records": "12,778", "country": "Romania"},
    {"name": "Finland B2B Procurement Winners — 11,694 Companies", "price": "149", "file": "ted_winners_FIN.csv", "records": "11,694", "country": "Finland"},
    {"name": "Netherlands B2B Procurement Winners — 10,639 Companies", "price": "149", "file": "ted_winners_NLD.csv", "records": "10,639", "country": "Netherlands"},
    {"name": "Belgium B2B Procurement Winners — 9,128 Companies", "price": "99", "file": "ted_winners_BEL.csv", "records": "9,128", "country": "Belgium"},
    {"name": "Bulgaria B2B Procurement Winners — 8,671 Companies", "price": "99", "file": "ted_winners_BGR.csv", "records": "8,671", "country": "Bulgaria"},
    {"name": "Austria B2B Procurement Winners — 8,262 Companies", "price": "99", "file": "ted_winners_AUT.csv", "records": "8,262", "country": "Austria"},
    {"name": "Norway B2B Procurement Winners — 8,261 Companies", "price": "99", "file": "ted_winners_NOR.csv", "records": "8,261", "country": "Norway"},
    {"name": "Hungary B2B Procurement Winners — 7,966 Companies", "price": "99", "file": "ted_winners_HUN.csv", "records": "7,966", "country": "Hungary"},
    {"name": "Denmark B2B Procurement Winners — 6,568 Companies", "price": "99", "file": "ted_winners_DNK.csv", "records": "6,568", "country": "Denmark"},
    {"name": "Ireland B2B Procurement Winners — 5,527 Companies", "price": "99", "file": "ted_winners_IRL.csv", "records": "5,527", "country": "Ireland"},
    {"name": "UK B2B Procurement Winners — 2,901 Companies", "price": "99", "file": "ted_winners_GBR.csv", "records": "2,901", "country": "UK"},
    {"name": "Norway Full Company Database — 324,000 Businesses with Email", "price": "999", "file": "norway_companies_314K.csv", "records": "324,000", "country": "Norway"},
]

DESC = """{records} verified B2B contacts from {country}. Companies that won EU public procurement contracts (TED 2020-2025). CSV with: company name, email, city, website, contract value, sector (CPV), authority, year. For B2B sales, recruitment, market research, lead generation. Official EU source, deduplicated."""


def create_product(page, product, index):
    """Creeaza un produs pe LemonSqueezy."""
    print(f"\n[{index}/{len(PRODUCTS)}] {product['name'][:50]}...")

    # Go to new product page
    page.goto("https://app.lemonsqueezy.com/products/new")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)

    # Product name
    name_input = page.locator("input[name='name']").first
    if name_input.is_visible():
        name_input.fill(product["name"])
    else:
        # Try alternative selectors
        page.locator("input[placeholder*='name' i], input[placeholder*='Name' i]").first.fill(product["name"])

    time.sleep(1)

    # Price
    price_input = page.locator("input[name='price']").first
    if price_input.is_visible():
        price_input.fill(product["price"])
    else:
        price_inputs = page.locator("input[type='number'], input[placeholder*='price' i]")
        if price_inputs.count() > 0:
            price_inputs.first.fill(product["price"])

    time.sleep(1)

    # Description
    desc_text = DESC.format(**product)
    desc_field = page.locator("textarea, [contenteditable='true'], [data-placeholder*='description' i]").first
    if desc_field.is_visible():
        desc_field.fill(desc_text)

    time.sleep(1)

    # File upload
    file_path = str(UPLOAD_DIR / product["file"])
    if os.path.exists(file_path):
        file_input = page.locator("input[type='file']").first
        if file_input.count() > 0:
            file_input.set_input_files(file_path)
            print(f"  Upload: {product['file']}")
            time.sleep(3)  # Wait for upload
    else:
        print(f"  SKIP upload: {file_path} nu exista")

    # Save / Create
    time.sleep(1)
    save_btn = page.locator("button:has-text('Save'), button:has-text('Create'), button:has-text('Publish'), button[type='submit']").first
    if save_btn.is_visible():
        save_btn.click()
        time.sleep(3)
        print(f"  SALVAT")
    else:
        print(f"  NU am gasit buton Save — verifica manual")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="Start de la produsul N")
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Chromium separat cu profil propriu — NU depinde de Chrome
        pw_profile = str(Path.home() / ".pw-lemonsqueezy")
        context = p.chromium.launch_persistent_context(
            pw_profile,
            headless=False,
            viewport={"width": 1280, "height": 900},
            slow_mo=500,
        )
        page = context.pages[0] if context.pages else context.new_page()

        # Verifica login
        page.goto("https://app.lemonsqueezy.com/products")
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(3)

        if "login" in page.url.lower() or "sign" in page.url.lower():
            print("LOGHEAZA-TE IN FEREASTRA CHROMIUM — ai 3 minute")
            for _ in range(180):
                time.sleep(1)
                if "login" not in page.url.lower() and "sign" not in page.url.lower():
                    break
            if "login" in page.url.lower():
                print("Nu te-ai logat. Ruleaza din nou — sesiunea ramane salvata.")
                context.close()
                sys.exit(1)

        print(f"Logged in. URL: {page.url}")
        print(f"Creez {len(PRODUCTS)} produse...")

        for i, product in enumerate(PRODUCTS, 1):
            if i < args.start:
                continue
            try:
                create_product(page, product, i)
            except Exception as e:
                print(f"  EROARE: {e}")
                continue

        print(f"\nGata! Verifica: https://app.lemonsqueezy.com/products")
        context.close()


if __name__ == "__main__":
    main()
