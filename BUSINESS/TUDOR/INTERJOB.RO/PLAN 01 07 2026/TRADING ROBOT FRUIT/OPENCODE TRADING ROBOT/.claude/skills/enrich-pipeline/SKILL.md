# Enrich Pipeline Skill

Orchestreaza imbogatirea bazei de cumparatori cu date din 12+ surse externe.

## Arhitectura

```
enriched_final.csv (12,360 CUI, 18 coloane)
         │
         ▼
  ┌─────────────────────────────────────┐
  │  enrich_to_db.py                    │
  │  - citeste fiecare _ENRICH/*.csv    │
  │  - match dupa CUI                   │
  │  - construieste 50 coloane          │
  │  - scrie in grain.db + VegFru.db    │
  │  - export CSV 50 cols               │
  └─────────────────────────────────────┘
         │
         ├── grain.db (CAEN 4621/0111) ───→ grain_buyer_match.py
         └── VegFru.db (CAEN 4631/0113) ──→ fv_buyer_match.py
```

## Surse de date

| Sursa | Fisier | Randuri | Match dupa |
|-------|--------|---------|------------|
| GMP+ certificari | `enrich_certificari.csv` | 439 | CUI / nume |
| DSVSA autorizari | `enrich_dsvsa.csv` | 1,100 | CUI |
| BRM membri | `enrich_brm_membri.csv` | 78 | CUI |
| Insolventa | `enrich_insolventa.csv` | 4,337 | CUI |
| MFinante | `enrich_mfinante.csv` | 4,293 | CUI |
| MADR spatii | `enrich_madr_spatii.csv` | 5,762 | CUI |
| APIA plati | `enrich_apia.csv` | 1,255 | CUI |
| AFIR proiecte | `enrich_afir.csv` | 928 | CUI |
| Licitatii SEAP | `enrich_licitatii.csv` | 61 | CUI |
| Firme noi ONRC | `enrich_firme_noi.csv` | 1,205 | CUI |
| Email web | `enrich_email_web.csv` | 1,676 | CUI |
| Google Maps | `enrich_gmaps.csv` | 75 | CUI |
| COMEXT flows | `enrich_comext_flows.csv` | 1,213 | CUI |

## Agenti

- `enrich-gmp-agent` — certificari GMP+
- `enrich-dsvsa-agent` — autorizari sanitare
- `enrich-brm-agent` — membri BRM
- `enrich-mfinante-agent` — date financiare ANAF

## Rulare

```bash
# Pipeline complet
python GRAIN/_PIPELINE/enrich_to_db.py

# Doar GMP+ (rapid)
python GRAIN/_PIPELINE/enrich_to_db.py --quick

# Fetchers individuali (daca lipsesc fisierele)
python GRAIN/_PIPELINE/enrich_gmp_certificari.py
python GRAIN/_PIPELINE/enrich_brm_membri.py
python GRAIN/_PIPELINE/enrich_mfinante.py
```

## Output

- `DATA/grain.db` — parteneri cereale (CAEN 4621/0111) cu 50 coloane
- `DATA/VegFru.db` — parteneri F&V (CAEN 4631/0113) cu 50 coloane
- `DATA/trading_partners_50cols.csv` — export CSV complet
