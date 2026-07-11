# GRAIN DESK — CLAUDE.md

**2026-07-10** · Cereale (grau, porumb, orz, floarea-soarelui, rapita).

---

## NOILE SCRIPURI

### 1. `GRAIN/fix_matif_benchmark.py`
Repara endpoint-ul MATIF Euronext care era hardcodat cu contracte DEC2025 expirate. Calculeaza dinamic front-month-ul (EBM grau: Mar/May/Sep/Dec; EMA porumb: Mar/Jun/Sep/Dec) si încearca fallback la contractul anterior daca front-month da eroare.

```
python GRAIN/fix_matif_benchmark.py          # fetch + afiseaza
python GRAIN/fix_matif_benchmark.py --test    # arata URL-urile fara fetch
python GRAIN/fix_matif_benchmark.py --dry     # test fetch fara output
```

Integrare: inlocuieste `fetch_euronext_matif()` din `cereale_benchmark.py` cu apel la `fix_matif_benchmark.fetch_all()`.

### 2. `GRAIN/clean_cereal_offers.py`
Curata ofertele cereale din `trading_offers` (PG) de intrari false (newslettere, reclame, notificari social media). Detecteaza prin pattern matching in `raw_snippet` + `context`. Carantina = `internal_only=true` + `freshness_note`.

```
python GRAIN/clean_cereal_offers.py            # dry-run
python GRAIN/clean_cereal_offers.py --apply    # carantina (safe)
python GRAIN/clean_cereal_offers.py --delete   # hard delete
```

Azi: 2 intrari carantinate (`fv_20260710_05a3e8` — reclama masini, `fv_20260710_696f60` — newsletter). 6 ramase bune.

### 3. `GRAIN/extract_producers_by_caen.py`
Extrage producatori si comercianti dupa cod CAEN din `master_romania_companies`, cross-referentiat cu `afir_beneficiari` (email enrichment) si `dsvsa_companies` (depozite).

```
python GRAIN/extract_producers_by_caen.py
```

Output in `DATA/producers_by_caen/`:
| Fisier | Descriere | Randuri |
|--------|-----------|---------|
| `producatori_cereale.csv` | CAEN 0111 | 22 |
| `producatori_legume.csv` | CAEN 0113 | 6 |
| `comercianti_cereale.csv` | CAEN 4621 | 5.137 |
| `comercianti_legume_fructe.csv` | CAEN 4631 | 6.845 |
| `afir_cu_email.csv` | AFIR beneficiari cu email | 320 |
| `dsvsa_depozite.csv` | DSVSA depozite cereale/legume | 71 |
| `unified_all.csv` | Unic CUI (toate sursele) | 12.360 |

437 cu email, 71 DSVSA, 12.360 CUI unici in total.

---

## STAREA GRAIN DUPA CURATENIE

**PG `trading_offers` (category='cereal'):** 6 oferte valide:
- 2 oferte reale: `cer_20260709_61e0ef` (grau 250t 192EUR Constanta), `fv_inbox_20260630_tutoveanu_naut` (naut)
- 2 oferte partiale din email Agricost/Al Dahra
- 2 oferte fv pipeline cu grau/grau durum (FOB Constanta 1.2EUR/kg)

**Benchmark:** 5 randuri `constanta_fob` manual (grau 215, porumb 205, orz 190, floarea-soarelui 440, rapita 470 EUR/t). MATIF — de reparat cu `fix_matif_benchmark.py`.

**1 alerta spread** activa: grau oferit 192 vs benchmark 215 (-10.7%).

---

## IMBOGATIRE PRODUCATORI

### `GRAIN/full_enrich_pipeline.py`
Pipeline in 3 faze pentru imbogatirea listei de 12.360 CUI:

**Phase 1 — master_emails** (completat, 30s pe .21):
- Temp table JOIN pe `master_emails` (rapid, ~2s)
- Extrage: email, telefon, domeniu, industrie, nume firma
- Rezultat: 459 email, 9.408 telefon, 116 website

```
python GRAIN/full_enrich_pipeline.py --phase1              # dry-run
python GRAIN/full_enrich_pipeline.py --phase1 --apply      # scrie enriched_phase1.csv
```

**Phase 2 — termene.ro scraping** (nepornit):
- Scrapeaza `termene.ro/firma/{CUI}/` pentru CUI fara email
- Extrage: email, telefon, website din HTML
- 11.901 CUI de procesat, ~0.3s delay => ~1 ora
- Risc: rate-limit, IP ban la 12K requesturi

```
python GRAIN/full_enrich_pipeline.py --phase2                          # dry-run
python GRAIN/full_enrich_pipeline.py --phase2 --apply                  # scrie
python GRAIN/full_enrich_pipeline.py --phase2 --max=100                # testeaza 100
```

**Phase 3 — verificare + deduplicare** (nepornit):
- Valideaza email/telefon/website (regex)
- Deduplica dupa CUI (pastreaza cel mai bun email)
- Genereaza raport Markdown

```
python GRAIN/full_enrich_pipeline.py --phase3 --apply
```

**Pipeline complet:**
```
python GRAIN/full_enrich_pipeline.py --all --apply   # ruleaza toate 3 fazele
```

### Alternativa: companies_clean
`master_romania_companies` (sursa initiala) + `master_emails` (enrichment) functioneaza rapid.
`companies_clean` (40M+ randuri, fara index pe CUI) e prea mare pentru JOIN — necesita
creare index pe `companies_clean(cui)` (~30min) sau batch query (prea lent).

### `GRAIN/enrich_producer_emails.py`
Varianta simpla (doar email din master_emails), folosita initial:
```
python GRAIN/enrich_producer_emails.py --apply
```

## CE URMEAZA

1. **Phase 2 termene.ro** — testam cu `--max=50` sa vezi randamentul.
2. **Integreaza `fix_matif_benchmark` in `cereale_benchmark.py`**.
3. **Deploy unificat pe raspibig** — structura `grain_opencode/` + cron-uri.
4. **WhatsApp inbound** — hook `wa_inbound.py` la connector (azi send-only).
