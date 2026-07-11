# GMP+ Certification Agent

**Scop:** Fetch GMP+ feed safety certified companies from Romania, match against master buyer base, flag quality-signal.

**Input:** Azure Search proxy `app.gmpplus.org/api/public/proxy/azure-search/locations`
**Output:** `DATA/_ENRICH/enrich_certificari.csv` (~439 ROU, 152 active)
**Match rate:** ~6.6% (29/439 matched to master by name normalization)

**Status:** Ported from GRAIN TRADING ROBOT `CODE/enrich_gmp_certificari.py`. 70 lines, standard library only.
