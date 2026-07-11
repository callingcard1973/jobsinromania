# DSVSA Enrichment Agent

**Scop:** Flag buyers with DSVSA sanitary-veterinary authorization for feed/food storage.

**Input:** ANSVSA registry dump → `enrich_dsvsa.csv`
**Output:** `DATA/_ENRICH/enrich_dsvsa.csv` (~1,100 rows)
**Columns:** `cui`, `tip_autorizatie`, `adresa_unitate`, `spatiu_autorizat`

**Status:** Data already exists. Pipeline uses `tip_autorizatie` to set `depozit_licentiat` flag.
