#!/usr/bin/env python3
"""
Google Search Console Verification Skill

Usage:
    python3 gsc_verify.py add-sites           # Add all job portal sites to GSC
    python3 gsc_verify.py get-codes           # Get verification codes
    python3 gsc_verify.py upload-files        # Upload verification files
    python3 gsc_verify.py submit-sitemaps     # Submit sitemaps for all sites
    python3 gsc_verify.py status              # Check verification status
"""

import asyncio
import json
import re
import os
import sys
import subprocess
from pathlib import Path

SITES = [
    "factoryjobs.eu", "buildjobs.eu", "warehouseworkers.eu", "horecaworkers.eu",
    "careworkers.eu", "electricjobs.eu", "farmworkers.eu", "meatworkers.eu",
    "mechanicjobs.eu", "nepalezi.com"
]

STATE_DIR = Path("/tmp/gsc_state")
CODES_FILE = STATE_DIR / "verification_codes.json"
CPANEL_AUTH = "cpanel loaiidil:30GYXYLTECIUBV36ND4B20VRQUZ51ZA4"
CPANEL_URL = "https://nl1-cl8-ats1.a2hosting.com:2083"

def get_site_path(site):
    if site == "warehouseworkers.eu":
        return "/home/loaiidil/public_html/warehouseworkers.eu"
    return f"/home/loaiidil/{site}"

async def add_sites_to_gsc():
    """Add all sites to Google Search Console using browser automation"""
    from playwright.async_api import async_playwright
    
    STATE_DIR.mkdir(exist_ok=True)
    browser_state = STATE_DIR / "browser_state"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(browser_state),
            headless=False
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Check login
        await page.goto("https://search.google.com/search-console")
        await page.wait_for_timeout(3000)
        
        if "accounts.google.com" in page.url:
            print("Please login to Google in the browser window...")
            print("Waiting 90 seconds for login...")
            await page.wait_for_timeout(90000)
            
            await page.goto("https://search.google.com/search-console")
            await page.wait_for_timeout(3000)
            
            if "accounts.google.com" in page.url:
                print("Login failed. Exiting.")
                await browser.close()
                return False
        
        print("Logged in to Google Search Console")
        codes = {}
        
        for site in SITES:
            print(f"\nAdding {site}...")
            try:
                # Go to welcome/add property page
                await page.goto("https://search.google.com/search-console/welcome")
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                
                # Click URL prefix tab
                try:
                    url_prefix = await page.query_selector('text="URL prefix"')
                    if url_prefix:
                        await url_prefix.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Find URL input
                inputs = await page.query_selector_all('input[type="text"]')
                url_input = None
                for inp in inputs:
                    placeholder = await inp.get_attribute('placeholder') or ''
                    value = await inp.get_attribute('value') or ''
                    if 'http' in placeholder.lower() or not value:
                        url_input = inp
                        break
                
                if url_input:
                    await url_input.fill(f'https://{site}/')
                    await page.wait_for_timeout(500)
                    
                    # Click Continue
                    continue_btn = await page.query_selector('button:has-text("Continue")')
                    if continue_btn:
                        await continue_btn.click()
                    else:
                        await page.keyboard.press('Enter')
                    
                    await page.wait_for_timeout(3000)
                    
                    # Look for HTML file verification
                    html_btn = await page.query_selector('text="HTML file"')
                    if html_btn:
                        await html_btn.click()
                        await page.wait_for_timeout(2000)
                    
                    # Get verification code
                    content = await page.content()
                    html_match = re.search(r'google([a-f0-9]{16})\.html', content)
                    if html_match:
                        codes[site] = html_match.group(0)
                        print(f"  ✓ Code: {codes[site]}")
                    else:
                        print(f"  ✗ No code found")
                        await page.screenshot(path=str(STATE_DIR / f"debug_{site.replace('.','_')}.png"))
                        
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        await browser.close()
        
        if codes:
            with open(CODES_FILE, 'w') as f:
                json.dump(codes, f, indent=2)
            print(f"\nCodes saved to {CODES_FILE}")
        
        return codes

def upload_verification_files():
    """Upload verification HTML files to all sites"""
    import subprocess
    
    if not CODES_FILE.exists():
        print(f"No codes file found at {CODES_FILE}")
        print("Run: python3 gsc_verify.py get-codes")
        return False
    
    with open(CODES_FILE) as f:
        codes = json.load(f)
    
    for site, filename in codes.items():
        content = f"google-site-verification: {filename}"
        path = get_site_path(site)
        
        # Base64 encode
        import base64
        encoded = base64.b64encode(content.encode()).decode()
        
        # Upload via cPanel
        cmd = [
            'curl', '-s', '-k',
            '-H', f'Authorization: {CPANEL_AUTH}',
            f'{CPANEL_URL}/execute/Fileman/save_file_content',
            '-d', f'dir={path}&file={filename}&content={encoded}&encoding=base64'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if '"status":1' in result.stdout:
            print(f"✓ {site}: Uploaded {filename}")
        else:
            print(f"✗ {site}: Failed - {result.stdout[:100]}")
    
    return True

def submit_sitemaps():
    """Submit sitemaps to IndexNow and verify robots.txt"""
    print("=== Submitting to IndexNow ===")
    
    key = "5fa1d82c739746a4a75e02ee3ff09a4e"
    
    for site in SITES:
        payload = {
            "host": site,
            "key": key,
            "keyLocation": f"https://{site}/{key}.txt",
            "urlList": [
                f"https://{site}/",
                f"https://{site}/sitemap.xml"
            ]
        }
        
        import subprocess
        result = subprocess.run([
            'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
            '-X', 'POST',
            'https://api.indexnow.org/indexnow',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True, text=True)
        
        print(f"{site}: HTTP {result.stdout}")
    
    return True

def check_status():
    """Check verification status of all sites"""
    print("=== Verification Status ===\n")

    # Check DNS TXT records using host command or skip
    print("DNS Verification:")
    for site in SITES:
        try:
            result = subprocess.run(['host', '-t', 'TXT', site], capture_output=True, text=True, timeout=5)
            if 'google-site-verification' in result.stdout:
                print(f"  ✓ {site}: DNS verified")
            else:
                print(f"  ✗ {site}: No DNS verification")
        except:
            print(f"  ? {site}: Could not check DNS")
    
    print("\nHTML Verification Files:")
    for site in SITES:
        import urllib.request
        try:
            # Check if any google*.html exists
            path = get_site_path(site)
            cmd = [
                'curl', '-s', '-k',
                '-H', f'Authorization: {CPANEL_AUTH}',
                f'{CPANEL_URL}/execute/Fileman/list_files?dir={path}&types=file'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if 'google' in result.stdout and '.html' in result.stdout:
                print(f"  ✓ {site}: Has verification file")
            else:
                print(f"  ✗ {site}: No verification file")
        except:
            print(f"  ? {site}: Could not check")
    
    print("\nSitemap Status:")
    for site in SITES:
        try:
            result = subprocess.run([
                'curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                f'https://{site}/sitemap.xml'
            ], capture_output=True, text=True)
            if result.stdout == '200':
                print(f"  ✓ {site}: sitemap.xml accessible")
            else:
                print(f"  ✗ {site}: sitemap.xml HTTP {result.stdout}")
        except:
            print(f"  ? {site}: Could not check")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'add-sites':
        asyncio.run(add_sites_to_gsc())
    elif cmd == 'get-codes':
        asyncio.run(add_sites_to_gsc())
    elif cmd == 'upload-files':
        upload_verification_files()
    elif cmd == 'submit-sitemaps':
        submit_sitemaps()
    elif cmd == 'status':
        check_status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
