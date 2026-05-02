#!/usr/bin/env python3
"""
Brevo DNS Authentication Skill — add all required DNS records for Brevo domain authentication.
Adds: brevo-code TXT, DKIM 1+2 CNAME, DMARC TXT, SPF include.

Usage:
    python3 brevo_dns_auth.py electricjobs.eu \
        --brevo-code dddc7f78136651c1a527606a90704b67 \
        --dkim-slug electricjobs-eu

    python3 brevo_dns_auth.py --check warehouseworkers.eu

Location: /opt/ACTIVE/INFRA/SKILLS/brevo_dns_auth.py
"""
import os, sys, argparse, requests, json, base64
from dotenv import load_dotenv

load_dotenv("/opt/ACTIVE/SCRAPERS/EUROPE/.env")

SERVER = "nl1-cl8-ats1.a2hosting.com"
USER = "loaiidil"
TOKEN = os.getenv("A2_CPANEL_API_TOKEN", "")
HEADERS = {"Authorization": f"cpanel {USER}:{TOKEN}"}


def get_zone(zone):
    r = requests.get(f"https://{SERVER}:2083/execute/DNS/parse_zone",
        headers=HEADERS, params={"zone": zone}, timeout=15, verify=True)
    return r.json().get("data", [])


def get_serial(data):
    for rec in data:
        if rec.get("record_type") == "SOA":
            return base64.b64decode(rec["data_b64"][2]).decode()
    return None


def add_record(zone, serial, dname, ttl, record_type, data_list):
    rec = json.dumps({"dname": dname, "ttl": ttl, "record_type": record_type, "data": data_list})
    r = requests.get(f"https://{SERVER}:2083/execute/DNS/mass_edit_zone",
        headers=HEADERS,
        params={"zone": zone, "serial": serial, "add": rec},
        timeout=15, verify=True)
    resp = r.json()
    return resp.get("status") == 1, resp.get("errors")


def remove_record(zone, serial, line_index):
    r = requests.get(f"https://{SERVER}:2083/execute/DNS/mass_edit_zone",
        headers=HEADERS,
        params={"zone": zone, "serial": serial, "remove": str(line_index)},
        timeout=15, verify=True)
    resp = r.json()
    return resp.get("status") == 1, resp.get("errors")


def check_domain(zone):
    """Check Brevo authentication status for a domain."""
    data = get_zone(zone)
    found = {"brevo_code": False, "dkim1": False, "dkim2": False, "dmarc": False, "spf_brevo": False}

    for rec in data:
        rt = rec.get("record_type", "")
        name = rec.get("dname_raw", "").rstrip(".")
        if rt == "TXT" and rec.get("data_b64"):
            txt = base64.b64decode(rec["data_b64"][0]).decode()
            if name == zone and "brevo-code:" in txt:
                found["brevo_code"] = True
                print(f"  OK    brevo-code: {txt}")
            if name == f"_dmarc.{zone}" or name == "_dmarc":
                found["dmarc"] = True
                print(f"  OK    DMARC: {txt[:80]}")
            if name == zone and "v=spf1" in txt and "spf.brevo.com" in txt:
                found["spf_brevo"] = True
                print(f"  OK    SPF: {txt[:80]}")
        if rt == "CNAME" and rec.get("data_b64"):
            val = base64.b64decode(rec["data_b64"][0]).decode()
            if "brevo1._domainkey" in name:
                found["dkim1"] = True
                print(f"  OK    DKIM1: {name} -> {val}")
            if "brevo2._domainkey" in name:
                found["dkim2"] = True
                print(f"  OK    DKIM2: {name} -> {val}")

    missing = [k for k, v in found.items() if not v]
    if missing:
        print(f"\n  MISSING: {', '.join(missing)}")
    else:
        print(f"\n  ALL BREVO DNS RECORDS PRESENT")
    return len(missing) == 0


def authenticate(zone, brevo_code, dkim_slug):
    """Add all Brevo authentication DNS records."""
    data = get_zone(zone)
    serial = get_serial(data)
    if not serial:
        print("ERROR: no SOA serial")
        return False

    records = [
        (f"{zone}.", 14400, "TXT", [f"brevo-code:{brevo_code}"]),
        (f"brevo1._domainkey.{zone}.", 14400, "CNAME", [f"b1.{dkim_slug}.dkim.brevo.com."]),
        (f"brevo2._domainkey.{zone}.", 14400, "CNAME", [f"b2.{dkim_slug}.dkim.brevo.com."]),
        (f"_dmarc.{zone}.", 14400, "TXT", ["v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com"]),
    ]

    for dname, ttl, rtype, dlist in records:
        print(f"Adding {rtype}: {dname} -> {dlist[0][:60]}")
        ok, errors = add_record(zone, serial, dname, ttl, rtype, dlist)
        if ok:
            print(f"  OK")
            # Refresh serial
            data = get_zone(zone)
            serial = get_serial(data)
        else:
            print(f"  FAIL: {errors}")

    # Check SPF
    data = get_zone(zone)
    serial = get_serial(data)
    has_brevo_spf = False
    old_spf_lines = []
    for rec in data:
        if rec.get("record_type") == "TXT":
            name = rec.get("dname_raw", "").rstrip(".")
            txt = base64.b64decode(rec["data_b64"][0]).decode() if rec.get("data_b64") else ""
            if name == zone and "v=spf1" in txt:
                if "spf.brevo.com" in txt:
                    has_brevo_spf = True
                else:
                    old_spf_lines.append((rec.get("line_index"), txt))

    if not has_brevo_spf and old_spf_lines:
        print(f"\nFixing SPF to include spf.brevo.com...")
        # Remove old SPF records
        for line_idx, txt in reversed(old_spf_lines):
            ok, errors = remove_record(zone, serial, line_idx)
            if ok:
                print(f"  Removed old SPF (line {line_idx})")
                data = get_zone(zone)
                serial = get_serial(data)

        # Add new clean SPF
        new_spf = f"v=spf1 +a +mx +ip4:209.124.66.6 include:spf.brevo.com include:spf.a2hosting.com ~all"
        ok, errors = add_record(zone, serial, f"{zone}.", 14400, "TXT", [new_spf])
        if ok:
            print(f"  Added new SPF: {new_spf[:80]}")

    print(f"\nVerification:")
    return check_domain(zone)


def main():
    p = argparse.ArgumentParser(description="Brevo DNS Authentication")
    p.add_argument("domain", nargs="?", help="Domain to authenticate")
    p.add_argument("--check", metavar="DOMAIN", help="Check domain authentication")
    p.add_argument("--brevo-code", help="Brevo verification code")
    p.add_argument("--dkim-slug", help="DKIM slug (e.g., electricjobs-eu)")
    args = p.parse_args()

    if args.check:
        check_domain(args.check)
    elif args.domain and args.brevo_code and args.dkim_slug:
        authenticate(args.domain, args.brevo_code, args.dkim_slug)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
