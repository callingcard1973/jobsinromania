#!/usr/bin/env python3
"""Publish all 19 products on LemonSqueezy via Brave CDP. No questions asked."""
import time, os
from pathlib import Path
from playwright.sync_api import sync_playwright

UPLOAD_DIR = Path(__file__).parent

PRODUCTS = [
    {"name": "Germany B2B Procurement Winners — 64,646 Companies", "price": "499", "file": "ted_winners_DEU.csv"},
    {"name": "France B2B Procurement Winners — 62,546 Companies", "price": "499", "file": "ted_winners_FRA.csv"},
    {"name": "Sweden B2B Procurement Winners — 29,409 Companies", "price": "299", "file": "ted_winners_SWE.csv"},
    {"name": "Poland B2B Procurement Winners — 28,209 Companies", "price": "299", "file": "ted_winners_POL.csv"},
    {"name": "Spain B2B Procurement Winners — 25,956 Companies", "price": "299", "file": "ted_winners_ESP.csv"},
    {"name": "Czech Republic B2B Procurement Winners — 18,406 Companies", "price": "199", "file": "ted_winners_CZE.csv"},
    {"name": "Italy B2B Procurement Winners — 16,750 Companies", "price": "199", "file": "ted_winners_ITA.csv"},
    {"name": "Romania B2B Procurement Winners — 12,778 Companies", "price": "149", "file": "ted_winners_ROU.csv"},
    {"name": "Finland B2B Procurement Winners — 11,694 Companies", "price": "149", "file": "ted_winners_FIN.csv"},
    {"name": "Netherlands B2B Procurement Winners — 10,639 Companies", "price": "149", "file": "ted_winners_NLD.csv"},
    {"name": "Belgium B2B Procurement Winners — 9,128 Companies", "price": "99", "file": "ted_winners_BEL.csv"},
    {"name": "Bulgaria B2B Procurement Winners — 8,671 Companies", "price": "99", "file": "ted_winners_BGR.csv"},
    {"name": "Austria B2B Procurement Winners — 8,262 Companies", "price": "99", "file": "ted_winners_AUT.csv"},
    {"name": "Norway B2B Procurement Winners — 8,261 Companies", "price": "99", "file": "ted_winners_NOR.csv"},
    {"name": "Hungary B2B Procurement Winners — 7,966 Companies", "price": "99", "file": "ted_winners_HUN.csv"},
    {"name": "Denmark B2B Procurement Winners — 6,568 Companies", "price": "99", "file": "ted_winners_DNK.csv"},
    {"name": "Ireland B2B Procurement Winners — 5,527 Companies", "price": "99", "file": "ted_winners_IRL.csv"},
    {"name": "UK B2B Procurement Winners — 2,901 Companies", "price": "99", "file": "ted_winners_GBR.csv"},
    {"name": "Norway Full Company Database — 324,000 Businesses", "price": "999", "file": "norway_companies_314K.csv"},
]

DESC = "Verified B2B contacts from official EU procurement records (TED 2020-2025). CSV: company name, email, city, website, contract value, sector. For B2B sales, recruitment, market research."

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]

    for i, prod in enumerate(PRODUCTS, 1):
        print(f"[{i}/{len(PRODUCTS)}] {prod['name'][:50]}...", flush=True)
        page = ctx.new_page()

        try:
            page.goto("https://app.lemonsqueezy.com/products/new", wait_until="domcontentloaded")
            time.sleep(4)

            # Screenshot to see what we're working with
            if i == 1:
                page.screenshot(path=str(UPLOAD_DIR / "debug_screenshot.png"))
                print(f"  Screenshot saved: debug_screenshot.png")

            # Try to fill product name
            filled = False
            for selector in [
                "input[name='name']",
                "input[placeholder*='name' i]",
                "input[placeholder*='Name' i]",
                "#name",
                "input[type='text']",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=2000):
                        el.fill(prod["name"])
                        filled = True
                        print(f"  Name filled via {selector}")
                        break
                except:
                    continue

            if not filled:
                # Try all visible text inputs
                inputs = page.locator("input[type='text'], input:not([type])")
                for idx in range(min(inputs.count(), 5)):
                    try:
                        inp = inputs.nth(idx)
                        if inp.is_visible():
                            inp.fill(prod["name"])
                            print(f"  Name filled via input #{idx}")
                            filled = True
                            break
                    except:
                        continue

            time.sleep(1)

            # Price
            for selector in [
                "input[name='price']",
                "input[placeholder*='price' i]",
                "input[placeholder*='Price' i]",
                "input[type='number']",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=2000):
                        el.fill(prod["price"])
                        print(f"  Price filled: {prod['price']}")
                        break
                except:
                    continue

            time.sleep(1)

            # Description
            for selector in [
                "textarea",
                "[contenteditable='true']",
                ".ProseMirror",
                "[data-placeholder]",
                ".ql-editor",
                "[role='textbox']",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        page.keyboard.type(DESC)
                        print(f"  Description filled")
                        break
                except:
                    continue

            time.sleep(1)

            # File upload
            fpath = str(UPLOAD_DIR / prod["file"])
            if os.path.exists(fpath):
                try:
                    file_input = page.locator("input[type='file']")
                    if file_input.count() > 0:
                        file_input.first.set_input_files(fpath)
                        print(f"  File uploaded: {prod['file']}")
                        time.sleep(5)
                except Exception as e:
                    print(f"  File upload skip: {e}")

            # Save/Create/Publish
            time.sleep(1)
            for btn_text in ["Create product", "Create", "Save", "Publish", "Submit"]:
                try:
                    btn = page.locator(f"button:has-text('{btn_text}')").first
                    if btn.is_visible(timeout=1000):
                        btn.click()
                        print(f"  Clicked: {btn_text}")
                        time.sleep(3)
                        break
                except:
                    continue

            print(f"  DONE — URL: {page.url}")

        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            page.close()

        time.sleep(2)

    print(f"\nFINISHED — {len(PRODUCTS)} products")
    print("Check: https://app.lemonsqueezy.com/products")
