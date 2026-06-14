#!/usr/bin/env python3
"""DMARC report parser: reads .xml/.gz reports from inbox folder, stores in dmarc_reports.
Reports arrive at dmarc@interjob.ro etc. fetched or dumped to /opt/ACTIVE/EMAIL/DMARC_INBOX/."""
import psycopg2, gzip, os
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

DB = dict(host="localhost", dbname="interjob_master", user="tudor", password="REDACTED")
INBOX = Path("/opt/ACTIVE/EMAIL/DMARC_INBOX")
INBOX.mkdir(parents=True, exist_ok=True)
PROCESSED = INBOX / "processed"
PROCESSED.mkdir(exist_ok=True)

def parse_report(path):
    try:
        if str(path).endswith(".gz"):
            with gzip.open(path, "rb") as fh:
                data = fh.read()
        else:
            with open(path, "rb") as fh:
                data = fh.read()
        root = ET.fromstring(data)
    except Exception as e:
        print(f"parse fail {path}: {e}"); return []
    rep = root.find("report_metadata")
    org = rep.findtext("org_name") if rep is not None else ""
    pol = root.find("policy_published")
    domain = pol.findtext("domain") if pol is not None else ""
    out = []
    for rec in root.findall("record"):
        row = rec.find("row")
        if row is None: continue
        src_ip = row.findtext("source_ip") or ""
        count = int(row.findtext("count") or 0)
        pol_eval = row.find("policy_evaluated")
        disposition = pol_eval.findtext("disposition") if pol_eval is not None else "none"
        spf = (pol_eval.findtext("spf") if pol_eval is not None else "fail") == "pass"
        dkim = (pol_eval.findtext("dkim") if pol_eval is not None else "fail") == "pass"
        out.append((domain, org, src_ip, count, disposition, spf, dkim))
    return out

def main():
    files = list(INBOX.glob("*.xml")) + list(INBOX.glob("*.xml.gz")) + list(INBOX.glob("*.gz"))
    if not files:
        print("no new DMARC reports"); return
    conn = psycopg2.connect(**DB); cur = conn.cursor()
    total = 0
    today = datetime.now().date()
    for f in files:
        rows = parse_report(f)
        for domain, org, ip, count, disp, spf, dkim in rows:
            try:
                cur.execute(
                    "INSERT INTO dmarc_reports (domain, report_date, org_name, source_ip, count, disposition, spf_pass, dkim_pass) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (domain, today, org, ip if ip else None, count, disp, spf, dkim))
                total += 1
            except Exception as e:
                conn.rollback()
                print(f"insert fail: {e}")
        else:
            conn.commit()
        f.rename(PROCESSED / f.name)
    conn.close()
    print(f"parsed {total} records from {len(files)} files")

if __name__ == "__main__": main()
