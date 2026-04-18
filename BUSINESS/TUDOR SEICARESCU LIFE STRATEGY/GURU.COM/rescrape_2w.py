#!/usr/bin/env python3
"""Delete last 14 days records and reset state for re-scrape."""
import psycopg2
import json
from pathlib import Path

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql", "port": 5432}
conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("SELECT id FROM beneficiari_privati WHERE TO_DATE(data_publicare, 'DD.MM.YYYY') >= CURRENT_DATE - 14")
ids = [r[0] for r in cur.fetchall()]
print(f"Found {len(ids)} anunturi from last 14 days")

cur.execute("DELETE FROM beneficiari_privati WHERE TO_DATE(data_publicare, 'DD.MM.YYYY') >= CURRENT_DATE - 14")
conn.commit()
print(f"Deleted {len(ids)} for re-scrape")

state_file = Path("/opt/ACTIVE/EU_FUNDING/DATA/BENEFICIAR_FONDURI_UE/state_anunturi.json")
if state_file.exists():
    state = json.load(open(state_file))
    state["scraped"] = [s for s in state["scraped"] if s not in ids]
    state["page"] = 0
    json.dump(state, open(state_file, "w"))
    print("State reset")

conn.close()
print("Ready for re-scrape")
