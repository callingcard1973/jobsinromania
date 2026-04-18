#!/usr/bin/env python3
"""Enable DKIM + SPF for ALL A2 Hosting email domains via cPanel API.
Checks current status, generates DKIM keys, installs DNS records.
Usage: python3 a2_dkim_setup.py [--status] [--fix]
"""
import requests, json, sys, os

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = os.environ.get("A2_CPANEL_API_TOKEN", "9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX")
HEADERS = {"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"}

DOMAINS = [
    "buildjobs.eu", "factoryjobs.eu", "warehouseworkers.eu", "interjob.ro",
    "mivromania.info", "mivromania.online", "careworkers.eu", "nepalezi.com",
    "expatsinromania.org", "horecaworkers.eu", "meatworkers.eu", "electricjobs.eu",
    "mechanicjobs.eu", "farmworkers.eu", "horecaworkers2026.com",
    "horecaworkers2026.eu", "horecaworkers2026.online", "aluminumrecyclehub.com",
    "cumparlegume.com", "seicarescu.com", "agroevolution.com", "cifn.info",
    "internaltransfers.eu",
]

def api_call(module, func, params=None):
    url = f"{CPANEL_HOST}/execute/{module}/{func}"
    try:
        r = requests.get(url, headers=HEADERS, params=params or {}, timeout=15, verify=True)
        return r.json() if r.ok else {"errors": [f"HTTP {r.status_code}"]}
    except Exception as e:
        return {"errors": [str(e)]}

def check_domain(domain):
    """Check email deliverability status for a domain."""
    result = api_call("Email", "get_main_account_status")
    # Try domain-specific check
    result2 = api_call("Email", "list_pops", {"domain": domain})
    return result2

def get_dkim_status(domain):
    """Check DKIM status via DNS lookup."""
    result = api_call("EmailAuth", "validate_current_dkims", {"domain": domain})
    return result

def enable_dkim(domain):
    """Enable DKIM for a domain."""
    # Install DKIM
    result = api_call("EmailAuth", "install_dkim_private_keys", {"domain": domain})
    if result.get("status") or result.get("data"):
        return True, "DKIM key installed"
    # Try ensure method
    result2 = api_call("EmailAuth", "ensure_dkim_keys_present", {"domain": domain})
    if result2.get("status") or result2.get("data"):
        return True, "DKIM ensured"
    return False, str(result.get("errors", result2.get("errors", "unknown")))

def enable_spf(domain):
    """Ensure SPF record exists."""
    result = api_call("EmailAuth", "install_spf_records", {"domain": domain})
    if result.get("status") or result.get("data"):
        return True, "SPF installed"
    return False, str(result.get("errors", "unknown"))

def validate_all(domain):
    """Validate DKIM + SPF for domain."""
    result = api_call("EmailAuth", "validate_current_ptrs", {"domain": domain})
    result2 = api_call("EmailAuth", "validate_current_spfs", {"domain": domain})
    result3 = api_call("EmailAuth", "validate_current_dkims", {"domain": domain})
    def extract_state(r):
        d = r.get("data", r.get("result", "?"))
        if isinstance(d, list):
            return d[0].get("state", "?") if d and isinstance(d[0], dict) else str(d)[:20]
        if isinstance(d, dict):
            return d.get("state", str(d)[:20])
        return str(d)[:20]
    return {"ptr": extract_state(result), "spf": extract_state(result2), "dkim": extract_state(result3)}

def main():
    status_only = "--status" in sys.argv
    fix = "--fix" in sys.argv

    if not status_only and not fix:
        print("Usage: python3 a2_dkim_setup.py --status   (check all)")
        print("       python3 a2_dkim_setup.py --fix      (enable DKIM+SPF for all)")
        return

    print(f"{'Domain':30s} {'DKIM':8s} {'SPF':8s} {'Action':20s}")
    print("-" * 70)

    for domain in DOMAINS:
        # Check current status
        v = validate_all(domain)
        dkim = v.get("dkim", "?")
        spf = v.get("spf", "?")

        action = ""
        if fix:
            if "VALID" not in str(dkim).upper():
                ok, msg = enable_dkim(domain)
                action += f"DKIM:{'OK' if ok else 'FAIL'} "
            if "VALID" not in str(spf).upper():
                ok, msg = enable_spf(domain)
                action += f"SPF:{'OK' if ok else 'FAIL'} "
            if not action:
                action = "already OK"

        print(f"{domain:30s} {str(dkim):8s} {str(spf):8s} {action}")

if __name__ == "__main__":
    main()
