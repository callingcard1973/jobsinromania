#!/usr/bin/env python3
import json

CFG = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/anofm.json"
with open(CFG) as f:
    d = json.load(f)

BRANDING = {
    "TUDOR_WAREHOUSE":        {"sender_brand": "WarehouseWorkers.eu",  "sender_url": "https://warehouseworkers.eu",   "sender_tagline": "Specialisti depozit si logistica pentru Europa"},
    "ANOFM_GMAIL1":           {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_GMAIL2":           {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_GMAIL3":           {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_GMAIL4":           {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_BREVO_ELECTRIC":   {"sender_brand": "ElectricJobs.eu",      "sender_url": "https://electricjobs.eu",       "sender_tagline": "Electricieni si tehnicieni pentru Europa"},
    "ANOFM_BREVO_NEPAL":      {"sender_brand": "CareWorkers.eu",       "sender_url": "https://careworkers.eu",        "sender_tagline": "Personal medical si ingrijire pentru Europa"},
    "ANOFM_BREVO_MEAT":       {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Muncitori industria alimentara pentru Europa"},
    "ANOFM_BREVO_EXPATS":     {"sender_brand": "ExpatsInRomania.org",  "sender_url": "https://expatsinromania.org",   "sender_tagline": "Forta de munca internationala pentru Romania"},
    "ANOFM_BREVO_HORECA26":   {"sender_brand": "HorecaWorkers.eu",     "sender_url": "https://horecaworkers2026.eu",  "sender_tagline": "Personal HORECA pentru Europa"},
    "ANOFM_BREVO_MIV_ONLINE": {"sender_brand": "HorecaWorkers.eu",     "sender_url": "https://horecaworkers2026.eu",  "sender_tagline": "Personal HORECA pentru Europa"},
    "ANOFM_LUCIAN":           {"sender_brand": "BP&P Partners",        "sender_url": "https://bppltd.co.uk",          "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_VIRGIL":           {"sender_brand": "BP&P Partners",        "sender_url": "https://bppltd.co.uk",          "sender_tagline": "Agentie recrutare internationala"},
    "ANOFM_ZOHO_YAHOO":       {"sender_brand": "InterJob Solutions",   "sender_url": "https://interjob.ro",           "sender_tagline": "Agentie recrutare internationala"},
}

for sector, vals in BRANDING.items():
    if sector in d.get("sectors", {}):
        d["sectors"][sector].update(vals)
        print(f"  {sector} -> {vals['sender_brand']}")

with open(CFG, "w") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print("anofm.json updated")
