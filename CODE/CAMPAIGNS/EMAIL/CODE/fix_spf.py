import requests, json

HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
H = {"Authorization": "cpanel loaiidil:9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX"}

domains = ["horecaworkers.eu", "meatworkers.eu", "mechanicjobs.eu", "farmworkers.eu", "mivromania.online"]

for d in domains:
    print(f"\n=== {d} ===")

    # Get current DNS zone records
    r = requests.get(f"{HOST}/execute/DNS/parse_zone", headers=H, params={"zone": d}, timeout=15)
    if not r.ok:
        print(f"  Cannot read zone: {r.status_code}")
        continue

    records = r.json().get("data", [])
    spf_records = [rec for rec in records if rec.get("type") == "TXT" and "spf" in str(rec.get("txtdata", rec.get("data_b64", ""))).lower()]

    if not spf_records:
        # Also check raw TXT records
        spf_records = [rec for rec in records if rec.get("type") == "TXT" and "v=spf1" in str(rec.get("txtdata", rec.get("record", ""))).lower()]

    print(f"  Found {len(spf_records)} SPF records:")
    for s in spf_records:
        line_num = s.get("line", s.get("Line", "?"))
        txt = s.get("txtdata", s.get("record", s.get("data_b64", "?")))
        print(f"    line {line_num}: {txt}")

    if len(spf_records) > 1:
        # Merge: combine all includes into one SPF record
        includes = set()
        for s in spf_records:
            txt = str(s.get("txtdata", s.get("record", "")))
            # Extract include: directives
            import re
            for m in re.findall(r"include:(\S+)", txt):
                includes.add(m)
            for m in re.findall(r"(ip4:\S+)", txt):
                includes.add(m)
            for m in re.findall(r"(\+?a\b)", txt):
                includes.add("a")
            for m in re.findall(r"(\+?mx\b)", txt):
                includes.add("mx")

        # Build merged SPF
        parts = ["v=spf1"]
        if "a" in includes:
            parts.append("+a")
            includes.discard("a")
        if "mx" in includes:
            parts.append("+mx")
            includes.discard("mx")
        for inc in sorted(includes):
            if inc.startswith("ip4:"):
                parts.append(inc)
            else:
                parts.append(f"include:{inc}")
        parts.append("~all")
        merged = " ".join(parts)
        print(f"  Merged SPF: {merged}")

        # Delete old SPF records
        for s in spf_records:
            line_num = s.get("line", s.get("Line"))
            if line_num:
                r_del = requests.get(f"{HOST}/execute/DNS/mass_edit_zone",
                    headers=H, params={"zone": d, "remove": line_num}, timeout=15)

        # Add merged SPF
        r_add = requests.get(f"{HOST}/execute/DNS/mass_edit_zone",
            headers=H, params={"zone": d, "add": json.dumps({"dname": d + ".", "ttl": 14400, "record_type": "TXT", "data": [merged]})}, timeout=15)
        print(f"  Merge result: {r_add.status_code} {r_add.json().get('status', '?')}")

    elif len(spf_records) == 0:
        # No SPF - create one with A2 + Brevo
        spf = "v=spf1 +a +mx include:_spf.a2hosting.com include:spf.sendinblue.com ~all"
        r_add = requests.get(f"{HOST}/execute/DNS/mass_edit_zone",
            headers=H, params={"zone": d, "add": json.dumps({"dname": d + ".", "ttl": 14400, "record_type": "TXT", "data": [spf]})}, timeout=15)
        print(f"  Created SPF: {spf}")
        print(f"  Result: {r_add.status_code}")
