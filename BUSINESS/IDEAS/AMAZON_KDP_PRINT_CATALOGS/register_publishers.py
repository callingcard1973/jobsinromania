"""Register at free book publishers with Playwright (visible browser)."""
import time
from playwright.sync_api import sync_playwright

EMAIL = "apaminerala@yahoo.com"
PASSWORD = "5c5Kr1&C&d2Jr8da"

def register_lulu(page):
    print("\n=== LULU.COM ===")
    page.goto("https://www.lulu.com/register")
    time.sleep(2)
    # Try to fill signup form
    try:
        page.fill('input[name="email"], input[type="email"]', EMAIL, timeout=5000)
        page.fill('input[name="password"], input[type="password"]', PASSWORD, timeout=5000)
        print("  Filled email + password")
        print("  >>> YOU: solve CAPTCHA if any, click Submit, verify email")
    except Exception as e:
        print(f"  Form not found ({e}) — fill manually")
    input("  Press Enter when Lulu signup is done...")

def register_draft2digital(page):
    print("\n=== DRAFT2DIGITAL ===")
    page.goto("https://draft2digital.com/signup")
    time.sleep(2)
    try:
        inputs = page.query_selector_all('input[type="email"], input[name="email"]')
        if inputs:
            inputs[0].fill(EMAIL)
        pwd_inputs = page.query_selector_all('input[type="password"]')
        if pwd_inputs:
            pwd_inputs[0].fill(PASSWORD)
        print("  Filled email + password")
        print("  >>> YOU: solve CAPTCHA if any, click Submit, verify email")
    except Exception as e:
        print(f"  Form not found ({e}) — fill manually")
    input("  Press Enter when D2D signup is done...")

def register_bookvault(page):
    print("\n=== BOOKVAULT ===")
    page.goto("https://app.bookvault.app/register")
    time.sleep(2)
    try:
        page.fill('input[name="email"], input[type="email"]', EMAIL, timeout=5000)
        page.fill('input[name="password"], input[type="password"]', PASSWORD, timeout=5000)
        print("  Filled email + password")
        print("  >>> YOU: solve CAPTCHA if any, click Submit, verify email")
    except Exception as e:
        print(f"  Form not found ({e}) — fill manually")
    input("  Press Enter when Bookvault signup is done...")

def register_kdp(page):
    print("\n=== AMAZON KDP ===")
    page.goto("https://kdp.amazon.com")
    time.sleep(2)
    print("  >>> YOU: sign in with your Amazon account")
    print("  >>> Then complete tax info + bank details")
    input("  Press Enter when KDP setup is done...")

def main():
    print("Book Publisher Registration — Visible Browser")
    print(f"Email: {EMAIL}")
    print(f"Password: {PASSWORD}")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, slow_mo=500,
            channel="msedge",
        )
        context = browser.new_context()
        page = context.new_page()

        register_lulu(page)
        register_draft2digital(page)
        register_bookvault(page)
        register_kdp(page)

        print("\n=== ALL DONE ===")
        print("Accounts created at: Lulu, Draft2Digital, Bookvault, KDP")
        browser.close()

if __name__ == "__main__":
    main()
