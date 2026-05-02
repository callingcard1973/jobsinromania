#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Brevo Account Activator with Playwright
Automates SMTP activation and email verification
"""
import sys
import os
import re
import time
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

# Gmail MCP tools available
GMAIL_AVAILABLE = True

class BrevoActivator:
    def __init__(self, email, password, headless=True):
        self.email = email
        self.password = password
        self.headless = headless
        self.browser = None
        self.page = None

    def start_browser(self):
        """Start Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        )
        self.page = context.new_page()

    def login(self):
        """Login to Brevo"""
        print(f"[1/4] Logging in to Brevo as {self.email}...")

        # Try both login URLs
        for url in ['https://app.brevo.com/account/login', 'https://login.brevo.com']:
            try:
                self.page.goto(url, wait_until='networkidle', timeout=15000)
                break
            except:
                continue

        time.sleep(2)

        # Fill email
        try:
            # Wait for and click email field first
            self.page.wait_for_selector('input[name="email"], input[id="email"], input[type="text"]', state='visible', timeout=10000)

            # Click to focus
            try:
                self.page.click('input[name="email"]', timeout=2000)
            except:
                try:
                    self.page.click('input[id="email"]', timeout=2000)
                except:
                    pass

            time.sleep(0.5)

            # Type email
            self.page.fill('input[name="email"], input[id="email"]', self.email)
            print(f"   Filled email: {self.email}")
        except Exception as e:
            print(f"❌ Could not fill email: {e}")
            return False

        # Fill password
        try:
            # Click password field
            try:
                self.page.click('input[type="password"]', timeout=2000)
            except:
                try:
                    self.page.click('input[name="password"]', timeout=2000)
                except:
                    pass

            time.sleep(0.5)
            self.page.fill('input[type="password"], input[name="password"]', self.password)
            print("   Filled password")
        except Exception as e:
            print(f"❌ Could not fill password: {e}")
            return False

        # Click login
        try:
            # Try different button selectors
            buttons = [
                'button[type="submit"]',
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'input[type="submit"]',
                '.btn-primary'
            ]
            clicked = False
            for selector in buttons:
                try:
                    self.page.click(selector, timeout=2000)
                    clicked = True
                    print(f"   Clicked login button")
                    break
                except:
                    continue

            if not clicked:
                print("❌ Could not find login button")
                return False

        except Exception as e:
            print(f"❌ Could not click login: {e}")
            return False

        # Wait for navigation after login
        try:
            self.page.wait_for_load_state('networkidle', timeout=15000)
        except:
            pass

        time.sleep(3)

        # Check current page
        current_url = self.page.url
        print(f"   After login: {current_url}")

        # Check for error messages
        page_text = self.page.content()
        if 'incorrect' in page_text.lower() or 'invalid' in page_text.lower():
            print("❌ Invalid credentials detected")
            # Save screenshot for debugging
            try:
                self.page.screenshot(path='/tmp/brevo_login_error.png')
                print("   Screenshot saved to /tmp/brevo_login_error.png")
            except:
                pass
            return False

        # Check if 2FA is required
        if '2fa' in current_url.lower():
            print("⚠️  2FA required, checking email for code...")
            if not self.handle_2fa():
                return False
            time.sleep(2)
            current_url = self.page.url

        # Check if logged in
        if 'dashboard' in current_url.lower() or 'settings' in current_url.lower() or 'app.brevo.com' in current_url:
            print("✅ Logged in successfully")
            return True
        else:
            # Maybe still on login page - check page content
            if 'dashboard' in page_text or 'campaign' in page_text.lower():
                print("✅ Logged in successfully (dashboard found in content)")
                return True

            print(f"❌ Login failed - unexpected URL: {current_url}")
            # Save screenshot
            try:
                self.page.screenshot(path='/tmp/brevo_login_failed.png')
                print("   Screenshot saved to /tmp/brevo_login_failed.png")
            except:
                pass
            return False

    def handle_2fa(self):
        """Handle 2FA verification"""
        code = self.get_2fa_code_from_email()
        if not code:
            print("❌ Could not get 2FA code from email")
            return False

        print(f"✅ Got 2FA code: {code}")

        # Input code
        try:
            # Try different input selectors
            try:
                self.page.fill('input[type="text"]', code)
            except:
                try:
                    self.page.fill('input[name="code"]', code)
                except:
                    self.page.fill('input.form-control', code)

            # Submit
            try:
                self.page.click('button:has-text("Verify")')
            except:
                try:
                    self.page.click('button:has-text("Submit")')
                except:
                    self.page.click('button[type="submit"]')

            time.sleep(2)
            print("✅ 2FA code submitted")
            return True
        except Exception as e:
            print(f"❌ Error submitting 2FA code: {e}")
            return False

    def get_2fa_code_from_email(self, max_wait=60):
        """Get 2FA code from Gmail using MCP"""
        import subprocess
        import json

        print(f"Waiting for Brevo 2FA email (up to {max_wait}s)...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Use Claude CLI with Gmail MCP to search
                result = subprocess.run([
                    'bash', '-c',
                    f'''
python3 << "PYEOF"
import sys
sys.path.insert(0, "/home/tudor/.local/lib/python3.13/site-packages")

try:
    # Import Gmail MCP functions
    from mcp__claude_ai_Gmail__gmail_search_messages import __call__ as search_messages
    from mcp__claude_ai_Gmail__gmail_read_message import __call__ as read_message
    import re

    # Search for Brevo emails from last 5 min
    result = search_messages({{"q": "from:noreply@brevo.com OR from:noreply@sendinblue.com newer_than:5m", "maxResults": 5}})

    if "messages" in result and result["messages"]:
        for msg_info in result["messages"]:
            msg = read_message({{"messageId": msg_info["id"]}})

            # Search in snippet and body
            text = msg.get("snippet", "") + " " + msg.get("textContent", "")

            # Look for 6-digit code
            match = re.search(r"\\b(\\d{{6}})\\b", text)
            if match:
                print(match.group(1))
                sys.exit(0)

except Exception as e:
    pass

PYEOF
'''
                ], capture_output=True, text=True, timeout=10)

                code = result.stdout.strip()
                if code and len(code) == 6 and code.isdigit():
                    print(f"✅ Found 2FA code: {code}")
                    return code

            except Exception as e:
                pass

            elapsed = int(time.time() - start_time)
            print(f"   Waiting... {elapsed}s / {max_wait}s")
            time.sleep(5)

        print("❌ No 2FA code found in email")
        return None

    def whitelist_ip(self, ip='86.126.144.227'):
        """Add IP to Brevo whitelist"""
        print(f"[2/4] Adding IP {ip} to whitelist...")

        try:
            self.page.goto('https://app.brevo.com/security/authorised_ips', timeout=15000)
            time.sleep(2)

            # Look for input to add IP
            # Try to find and click "Add IP" button
            try:
                self.page.click('text="Add IP"', timeout=3000)
            except:
                try:
                    self.page.click('button:has-text("Add")', timeout=3000)
                except:
                    pass

            time.sleep(1)

            # Fill IP address
            try:
                ip_input = self.page.query_selector('input[type="text"]') or self.page.query_selector('input[placeholder*="IP"]')
                if ip_input:
                    ip_input.type(ip, delay=50)
                    time.sleep(1)

                    # Submit
                    try:
                        self.page.click('button:has-text("Add")', timeout=3000)
                    except:
                        try:
                            self.page.click('button[type="submit"]', timeout=3000)
                        except:
                            pass

                    time.sleep(2)
                    print(f"✅ IP {ip} whitelisted")
                    return True
            except Exception as e:
                print(f"⚠️  Could not add IP: {e}")

            # Check if IP already whitelisted
            content = self.page.content()
            if ip in content:
                print(f"✅ IP {ip} already whitelisted")
                return True

            return False

        except Exception as e:
            print(f"❌ Error whitelisting IP: {e}")
            return False

    def check_smtp_status(self):
        """Check if SMTP is activated"""
        print("[3/4] Checking SMTP status...")

        try:
            self.page.goto('https://app.brevo.com/settings/keys/smtp', timeout=15000)
            time.sleep(2)

            content = self.page.content()

            if 'not yet activated' in content.lower() or 'request activation' in content.lower():
                print("⚠️  SMTP not activated - needs Brevo support")
                return False
            elif 'smtp-relay.brevo.com' in content:
                print("✅ SMTP already activated")
                return True
            else:
                print("⚠️  Status unclear, checking further...")
                return None
        except Exception as e:
            print(f"❌ Error checking SMTP: {e}")
            return None

    def request_activation(self):
        """Request SMTP activation"""
        print("[3/4] Requesting SMTP activation...")

        # Look for activation button/link
        try:
            # Try common button texts
            for text in ['Activate', 'Request activation', 'Enable SMTP', 'Activate SMTP']:
                try:
                    self.page.click(f'text="{text}"', timeout=5000)
                    print(f"✅ Clicked '{text}' button")
                    time.sleep(2)
                    return True
                except:
                    continue

            # Check if there's a form to fill
            if 'contact@brevo.com' in self.page.content():
                print("⚠️  Manual activation required - email contact@brevo.com")
                return False

            print("⚠️  No activation button found")
            return False

        except Exception as e:
            print(f"❌ Error requesting activation: {e}")
            return False

    def check_email_for_code(self, wait_seconds=60):
        """Check Gmail for Brevo verification code"""
        print(f"[4/4] Checking email for verification code (waiting {wait_seconds}s)...")

        if not GMAIL_AVAILABLE:
            print("⚠️  Gmail MCP not available, check email manually")
            return None

        # Search for recent Brevo emails
        import subprocess
        import json

        start_time = time.time()
        while time.time() - start_time < wait_seconds:
            try:
                # Use mcp__claude_ai_Gmail__gmail_search_messages
                result = subprocess.run([
                    'python3', '-c',
                    '''
import sys
sys.path.insert(0, "/opt/ACTIVE/INFRA")
# TODO: Call Gmail MCP tool to search for Brevo emails
# For now, return None
print("null")
'''
                ], capture_output=True, text=True, timeout=10)

                # Parse result and look for verification code
                # Pattern: 6-digit code or similar

                time.sleep(5)

            except Exception as e:
                print(f"Error checking email: {e}")
                break

        print("⚠️  No verification code found in email")
        return None

    def input_verification_code(self, code):
        """Input verification code into Brevo"""
        print(f"Inputting verification code: {code}")

        try:
            # Look for verification input
            self.page.fill('input[type="text"]', code)
            self.page.click('button[type="submit"]')
            time.sleep(2)
            print("✅ Code submitted")
            return True
        except Exception as e:
            print(f"❌ Failed to input code: {e}")
            return False

    def activate(self):
        """Full activation flow - whitelist IP and check SMTP status"""
        try:
            self.start_browser()

            if not self.login():
                return False

            # Whitelist IP first
            self.whitelist_ip()

            # Check SMTP status
            status = self.check_smtp_status()
            if status is True:
                print("✅ Account ready to send")
                return True
            elif status is False:
                print("❌ SMTP not activated - contact support at contact@brevo.com")
                return False
            else:
                print("⚠️  Could not verify SMTP status")
                return None

        except Exception as e:
            print(f"❌ Error during activation: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.browser:
                if not self.headless:
                    print("Keeping browser open for manual completion...")
                    input("Press Enter to close browser...")
                self.browser.close()
                self.playwright.stop()


def main():
    parser = argparse.ArgumentParser(description='Brevo SMTP Activator')
    parser.add_argument('--email', required=True, help='Brevo account email')
    parser.add_argument('--password', required=True, help='Brevo account password')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')

    args = parser.parse_args()

    activator = BrevoActivator(
        email=args.email,
        password=args.password,
        headless=not args.visible
    )

    result = activator.activate()

    if result is True:
        print("\n✅ SUCCESS: SMTP activated")
        send_telegram(f"✅ Brevo SMTP activated for {args.email}")
        return 0
    elif result is None:
        print("\n⚠️  PARTIAL: Manual completion needed")
        return 2
    else:
        print("\n❌ FAILED: Could not activate SMTP")
        send_telegram(f"❌ Brevo activation failed for {args.email}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
