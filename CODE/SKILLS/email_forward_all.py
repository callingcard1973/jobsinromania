#!/usr/bin/env python3
"""
Email Forward All - Set up forwarding for all A2 Hosting email accounts
Excludes: unsubscribe@*, dmarc@*, noreply@*, loaiidil (system)
Forwards to: manpower.dristor@gmail.com, manpowerdristor@gmail.com
"""

import requests
import urllib3
import json
import sys
import time

urllib3.disable_warnings()

AUTH = "cpanel loaiidil:30GYXYLTECIUBV36ND4B20VRQUZ51ZA4"
BASE = "https://nl1-cl8-ats1.a2hosting.com:2083"
FORWARD_TO = ["manpower.dristor@gmail.com", "manpowerdristor@gmail.com"]
EXCLUDE_PREFIXES = ["unsubscribe@", "dmarc@", "noreply@"]
EXCLUDE_EXACT = ["loaiidil"]

def api_call(endpoint, params=None):
    headers = {"Authorization": AUTH}
    url = f"{BASE}/execute/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k,v in params.items())
    resp = requests.get(url, headers=headers, verify=False, timeout=30)
    return resp.json()

def add_forwarder(email, forward_to):
    """Add a single forwarder"""
    local, domain = email.split('@')
    result = api_call("Email/add_forwarder", {
        "domain": domain,
        "email": local,
        "fwdopt": "fwd",
        "fwdemail": forward_to
    })
    return result.get('status') == 1

def get_existing_forwarders():
    """Get set of existing forwarder pairs"""
    result = api_call("Email/list_forwarders")
    existing = set()
    for f in result.get('data', []):
        existing.add((f.get('dest', ''), f.get('forward', '')))
    return existing

def get_all_accounts():
    """Get all email accounts"""
    result = api_call("Email/list_pops")
    return [a.get('email') for a in result.get('data', [])]

def should_forward(email):
    """Check if email should be forwarded"""
    if email in EXCLUDE_EXACT:
        return False
    for prefix in EXCLUDE_PREFIXES:
        if email.startswith(prefix):
            return False
    return True

def main(dry_run=False):
    print("=== EMAIL FORWARD ALL ===")
    print(f"Forward to: {', '.join(FORWARD_TO)}")
    print(f"Exclude: {EXCLUDE_PREFIXES + EXCLUDE_EXACT}")
    print(f"Dry run: {dry_run}")
    print()
    
    accounts = get_all_accounts()
    existing = get_existing_forwarders()
    
    to_forward = [a for a in accounts if should_forward(a)]
    print(f"Accounts to forward: {len(to_forward)}/{len(accounts)}")
    print()
    
    added = 0
    skipped = 0
    
    for email in sorted(to_forward):
        for fwd in FORWARD_TO:
            if (email, fwd) in existing:
                skipped += 1
                continue
            
            if dry_run:
                print(f"  [DRY] {email} -> {fwd}")
                added += 1
            else:
                if add_forwarder(email, fwd):
                    print(f"  [OK] {email} -> {fwd}")
                    added += 1
                else:
                    print(f"  [FAIL] {email} -> {fwd}")
                time.sleep(0.2)
    
    print()
    print(f"=== COMPLETE ===")
    print(f"Added: {added} | Already existed: {skipped}")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    main(dry_run=dry_run)
