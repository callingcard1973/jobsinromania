# BRM Membership Agent

**Scop:** Scrape `brm.ro/membri` for Bursa Romana de Marfuri members, flag active commodity traders.

**Input:** BRM website members list
**Output:** `DATA/_ENRICH/enrich_brm_membri.csv` (~78 members)
**Match rate:** 0% (BRM uses CUI format that doesn't overlap with master)

**Status:** Ported. 50 lines, standard library.
