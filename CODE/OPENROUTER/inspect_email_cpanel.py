#!/usr/bin/env python3
"""Inspect email using cPanel API and analyze with OpenRouter."""

import asyncio
import httpx
import json
import base64
from pathlib import Path
from dotenv import load_dotenv

# Load env
if Path(__file__).parent.joinpath(".env").exists():
    load_dotenv(Path(__file__).parent / ".env")

from llm import complete


async def get_cpanel_token():
    """Get cPanel authentication token."""
    # From INTERJOB.RO/.env
    return "8EQMARBXKK2XJF3W84QTBV47NR4M344G"


async def inspect_via_cpanel(email_user, domain):
    """Inspect email account via cPanel API."""

    print("\n[EMAIL] Inspecting %s@%s via cPanel..." % (email_user, domain))

    token = await get_cpanel_token()
    host = "nl1-cl8-ats1.a2hosting.com"
    user = "loaiidil"

    # List email accounts
    url = f"https://{host}:2083/json-api/cpanel?cpanel_jsonapi_user={user}&cpanel_jsonapi_apiversion=2&cpanel_jsonapi_module=Email&cpanel_jsonapi_func=listpops"

    headers = {
        "Authorization": f"WHM {user}:{token}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers, timeout=30)

            print("[HTTP] Status: %d" % response.status_code)

            if response.status_code == 200:
                data = response.json()
                print("[OK] Connected to cPanel\n")

                # Find the email account
                print("Email Accounts on interjob.ro:")
                print("="*70)

                accounts = data.get('cpanelresult', {}).get('data', [])

                for account in accounts:
                    email = account.get('email', 'unknown')
                    quota_mb = int(account.get('diskquota_kb', 0)) / 1024
                    used_mb = int(account.get('diskused_kb', 0)) / 1024

                    if quota_mb > 0:
                        usage_pct = (used_mb / quota_mb) * 100
                    else:
                        usage_pct = 0

                    print("[ACCT] %s" % email)
                    print("       Quota: %.1f MB | Used: %.1f MB | Usage: %.1f%%" % (
                        quota_mb, used_mb, usage_pct))

                    if usage_pct > 80:
                        print("       [WARN] Over 80% full!")
                    print()

                # Analyze using AI
                account_info = "\n".join([
                    "- %s: %.1f MB / %.1f MB (%.1f%% full)" % (
                        a.get('email', 'unknown'),
                        int(a.get('diskused_kb', 0)) / 1024,
                        int(a.get('diskquota_kb', 0)) / 1024,
                        (int(a.get('diskused_kb', 0)) / max(int(a.get('diskquota_kb', 0)), 1)) * 100
                    )
                    for a in accounts
                ])

                prompt = """Email accounts on interjob.ro domain:

%s

Analyze why office@interjob.ro is full:
1. Is it a quota limit issue or real bloat?
2. What typically fills email accounts (spam, forwarding loops, auto-replies)?
3. How to investigate further (IMAP access, cPanel logs)?
4. Quick fixes (increase quota, delete old mail, disable forwarding)?

Be specific to A2 Hosting environment.""" % account_info

                print("[AI] Analyzing with OpenRouter (free)...\n")

                result = await complete(
                    prompt,
                    system="You are an email administrator for A2 Hosting. Provide practical solutions."
                )

                print("[REPORT] Analysis:")
                print(result)

            else:
                print("[ERROR] Status: %d" % response.status_code)
                print(response.text)

    except Exception as e:
        print("[ERROR] %s" % str(e))


async def main():
    await inspect_via_cpanel("office", "interjob.ro")


if __name__ == "__main__":
    asyncio.run(main())
