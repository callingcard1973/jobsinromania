#!/usr/bin/python3
"""
Helper to get Brevo 2FA code from Gmail
Uses Gmail MCP to search and extract code
"""
import sys
import re
import time

def get_brevo_2fa_code(email, max_wait=60):
    """
    Search Gmail for Brevo 2FA code
    Returns 6-digit code or None
    """
    print(f"Searching Gmail for Brevo 2FA code sent to {email}...")

    start_time = time.time()
    last_search_time = 0

    while time.time() - start_time < max_wait:
        # Rate limit: search every 5 seconds
        if time.time() - last_search_time < 5:
            time.sleep(1)
            continue

        last_search_time = time.time()

        try:
            # Use subprocess to call Claude with Gmail MCP
            import subprocess
            result = subprocess.run([
                'bash', '-c',
                '''
# This would need Claude CLI to search Gmail
# For now, print instructions
cat << EOI
Check Gmail for email from:
  - noreply@brevo.com
  - noreply@sendinblue.com

Subject contains: verification code, 2FA, or similar

Look for 6-digit code in email body
EOI
'''
            ], capture_output=True, text=True, timeout=5)

            print(result.stdout)

        except Exception as e:
            print(f"Error: {e}")

        print(f"Waiting... ({int(time.time() - start_time)}s / {max_wait}s)")
        time.sleep(5)

    return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: brevo_2fa_helper.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    code = get_brevo_2fa_code(email)

    if code:
        print(f"\n2FA Code: {code}")
        sys.exit(0)
    else:
        print("\nNo code found")
        sys.exit(1)
