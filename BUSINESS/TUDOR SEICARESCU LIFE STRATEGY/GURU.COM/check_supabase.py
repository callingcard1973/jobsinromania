#!/usr/bin/env python3
import requests
URL = "https://srgfzelqcehzidkzkjyx.supabase.co"
ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyZ2Z6ZWxxY2Voemlka3pranl4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2NTU1MjAsImV4cCI6MjA5MDIzMTUyMH0.ybQVkWw_UFDgqLqCGsOnTvt5weq0ps3N1sZmRSAb2gE"
H = {"apikey": ANON, "Authorization": "Bearer " + ANON}

# Try all possible table names
for tbl in ["beneficiari_privati", "anunturi", "proiecte", "proiecte_eu", "companies", "leads"]:
    r = requests.get(URL + "/rest/v1/" + tbl + "?limit=1", headers=H)
    status = r.status_code
    if status == 200:
        data = r.json()
        cols = list(data[0].keys()) if data else "empty"
        print(tbl + ": EXISTS - " + str(cols))
    else:
        print(tbl + ": " + str(status))
