#!/usr/bin/env python3
import requests, json
requests.packages.urllib3.disable_warnings()
from parsers import parse_proiect

r = requests.get("https://beneficiar.fonduri-ue.ro:8080/proiecte/details/1/15006/", verify=False, timeout=30)
d = parse_proiect(r.text, 15006)
print("Title:", d["titlu_proiect"])
print("SMIS:", d["cod_smis"])
print("Beneficiar:", d["beneficiar"])
procs = json.loads(d["proceduri"])
print("Procedures:", len(procs))
for p in procs:
    print("  %-10s %-12s %s" % (p["status"], p["deadline"], p["name"][:60]))
