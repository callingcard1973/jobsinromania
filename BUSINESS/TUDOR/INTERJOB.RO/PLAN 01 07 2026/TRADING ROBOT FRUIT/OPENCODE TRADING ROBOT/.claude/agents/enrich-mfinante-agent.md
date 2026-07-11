# MFinante Enrichment Agent

**Scop:** Download ANAF financial statements for CUI, classify company by `marime` (mica/medie/mare).

**Input:** CUI list from master
**Output:** `DATA/_ENRICH/enrich_mfinante.csv` (4,293/13,426 CUI covered)
**Coverage:** 2024: 3,858 CUI, 2023: 435 CUI (fallback)

**Status:** Ported. Caches downloads in `_anaf_bilant_2024/`.
