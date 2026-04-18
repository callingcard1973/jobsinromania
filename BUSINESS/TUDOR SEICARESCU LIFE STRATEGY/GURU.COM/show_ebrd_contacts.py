#!/usr/bin/env python3
import csv
with open("/opt/ACTIVE/SCRAPERS/EBRD/data/ebrd_psd_details.csv") as f:
    for r in csv.DictReader(f):
        if r.get("contact_email"):
            print("%-30s %-35s %-20s %s" % (r["contact_name"][:30], r["contact_email"][:35], r["contact_phone"][:20], r["country"]))
