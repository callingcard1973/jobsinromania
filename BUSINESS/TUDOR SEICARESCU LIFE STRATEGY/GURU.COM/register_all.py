#!/usr/bin/env python3
"""Register on freelance platforms using Edge with debug port.
Edge works with --remote-debugging-port on Windows (Chrome doesn't)."""

import subprocess
import time
import sys
import urllib.request
from playwright.sync_api import sync_playwright

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEBUG_PORT = 9222

TITLE = "Data Engineer & Python Developer | Web Scraping, Automation, 200M+ Records"

SUMMARY = (
    "I build data-driven automation systems processing 200M+ records"
    " across 42 countries. I turn raw, unstructured data into"
    " actionable business intelligence.\n\n"
    "What I deliver:\n"
    "- Web scraping: government portals, procurement platforms,"
    " business registries (Selenium, Playwright, BeautifulSoup, Scrapy)\n"
    "- PostgreSQL databases at scale (200M+ records, 13GB+) with"
    " enrichment pipelines and deduplication\n"
    "- Email campaign infrastructure: multi-sender orchestration,"
    " bounce management, warmup, DNC compliance\n"
    "- Telegram bots: lead capture, applicant tracking, automated"
    " alerts, admin dashboards\n"
    "- Python automation: ETL pipelines, cron/systemd services,"
    " API integrations, Flask dashboards\n\n"
    "Live infrastructure I manage daily:\n"
    "- 76+ running services across 3 Linux servers\n"
    "- 28 websites across 15 recruitment sectors\n"
    "- 25+ scheduled jobs (scraping, enrichment, campaigns, backups)\n"
    "- 6 Telegram channels with auto-publishing in 4 languages\n\n"
    "Industries: International recruitment, EU procurement/tenders,"
    " agriculture, construction, B2B lead generation, insolvency.\n\n"
    "Tech: Python 3, PostgreSQL, Bash, Selenium, Playwright,"
    " BeautifulSoup, Scrapy, Flask, Redis, Docker, Brevo API,"
    " Telegram Bot API, Node-RED, systemd, Linux."
)

SKILLS = [
    "Python", "PostgreSQL", "Web Scraping", "Data Mining",
    "Data Engineering", "ETL", "Automation", "Selenium",
    "Playwright", "Beautiful Soup", "Scrapy", "Flask",
    "Telegram Bot", "Email Marketing", "Lead Generation",
    "API Development", "Linux Administration", "Docker",
    "Database Design", "Data Enrichment", "B2B Lead Generation",
    "Market Research",
]

HOURLY_RATE = "35"


def pause(page, msg):
    print(f"  >> {msg}")
    try:
        safe = msg.replace("\\", "\\\\").replace("'", "\\'")
        page.evaluate(f"alert('{safe}')")
    except Exception:
        time.sleep(5)


def fill(page, selector, value, timeout=3000):
    try:
        el = page.wait_for_selector(selector, timeout=timeout)
        if el:
            el.click()
            el.fill(value)
            print(f"  Filled: {selector[:50]}")
            return True
    except Exception:
        pass
    return False


def get_edge():
    """Kill Edge, relaunch with debug port, wait until ready."""
    print("Killing Edge...")
    subprocess.run(["taskkill.exe", "//F", "//IM", "msedge.exe"],
                   capture_output=True)
    time.sleep(4)

    print(f"Launching Edge with --remote-debugging-port={DEBUG_PORT}...")
    subprocess.Popen([EDGE_EXE, f"--remote-debugging-port={DEBUG_PORT}"])

    print("Waiting for debug port...", end="", flush=True)
    for i in range(30):
        time.sleep(2)
        try:
            r = urllib.request.urlopen(
                f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=2
            )
            data = r.read().decode()
            if "webSocketDebuggerUrl" in data:
                print(f" ready! ({(i+1)*2}s)")
                return True
        except Exception:
            print(".", end="", flush=True)
    print(" FAILED")
    return False


def do_guru(page):
    print("\n=== GURU.COM ===")
    page.goto("https://www.guru.com/registeraccount.aspx")
    pause(page, "Register on Guru.com. Click OK when logged in.")
    page.goto("https://www.guru.com/settings/profile")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    fill(page, 'input[name*="tagline"], input[placeholder*="tagline"]', TITLE)
    fill(page, 'textarea[name*="description"], textarea[name*="summary"]', SUMMARY)
    fill(page, 'input[name*="rate"], input[placeholder*="rate"]', HOURLY_RATE)
    pause(page, "Review + save Guru profile. Click OK.")
    print("  DONE")


def do_upwork(page):
    print("\n=== UPWORK ===")
    page.goto("https://www.upwork.com/nx/signup/?dest=home")
    pause(page, "Register on Upwork + onboarding. Click OK when done.")
    page.goto("https://www.upwork.com/freelancers/settings/profile")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    fill(page, '[data-testid="title-input"], input[name="title"]', TITLE)
    fill(page, '[data-testid="overview-textarea"], textarea[name="overview"]', SUMMARY)
    pause(page, "Review Upwork profile. Click OK.")
    print("  DONE")


def do_fiverr(page):
    print("\n=== FIVERR ===")
    page.goto("https://www.fiverr.com/join")
    pause(page, "Register on Fiverr + become seller. Click OK.")
    gigs = [
        ("I will scrape any website and deliver clean data",
         "$50/$150/$500"),
        ("I will build a targeted B2B contact list with emails",
         "$75/$200/$500"),
        ("I will automate any repetitive task with Python",
         "$100/$300/$750"),
        ("I will build a custom Telegram bot with database",
         "$150/$400/$800"),
        ("I will set up automated email campaign infrastructure",
         "$200/$500/$1000"),
    ]
    for i, (title, prices) in enumerate(gigs):
        print(f"  Gig {i+1}/5: {title[:50]}...")
        page.goto("https://www.fiverr.com/manage_gigs/new")
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)
        fill(page, '#title, input[name="title"]', title)
        pause(page, f"Gig {i+1}: prices {prices}. Publish. Click OK.")
    print("  DONE")


def do_freelancer(page):
    print("\n=== FREELANCER.COM ===")
    page.goto("https://www.freelancer.com/signup")
    pause(page, "Register on Freelancer.com. Click OK when done.")
    page.goto("https://www.freelancer.com/users/settings/profile")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    fill(page, 'input[name*="tagline"], #professional-headline', TITLE)
    fill(page, 'textarea[name*="summary"], #profile-description', SUMMARY)
    pause(page, "Review Freelancer.com profile. Click OK.")
    print("  DONE")


def do_peopleperhour(page):
    print("\n=== PEOPLEPERHOUR ===")
    page.goto("https://www.peopleperhour.com/freelancer")
    pause(page, "Register on PeoplePerHour. Click OK when done.")
    page.goto("https://www.peopleperhour.com/freelancer/dashboard/profile")
    page.wait_for_load_state("networkidle", timeout=15000)
    time.sleep(2)
    fill(page, 'input[name*="tagline"], #tagline', TITLE)
    fill(page, 'textarea[name*="bio"], textarea[name*="description"]', SUMMARY)
    pause(page, "Review PeoplePerHour profile. Click OK.")
    print("  DONE")


PLATFORMS = {
    "guru": do_guru,
    "upwork": do_upwork,
    "fiverr": do_fiverr,
    "freelancer": do_freelancer,
    "peopleperhour": do_peopleperhour,
}


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(PLATFORMS.keys())
    print(f"Platforms: {', '.join(targets)}")

    if not get_edge():
        print("Could not connect to Edge. Exiting.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        print("Connected to Edge!\n")

        # First: let user login to Google if needed
        page.goto("https://accounts.google.com")
        pause(page, "Login to Google if not already logged in. Click OK when ready.")

        for name in targets:
            if name in PLATFORMS:
                try:
                    PLATFORMS[name](page)
                except Exception as e:
                    print(f"  ERROR on {name}: {e}")
                    pause(page, f"Error on {name}. Fix manually. Click OK.")

        print("\n=== ALL DONE ===")
        pause(page, "All platforms done! Click OK to finish.")


if __name__ == "__main__":
    main()
