---
name: fv-trading-orchestrator
description: "Orchestrator principal pentru TRADING ROBOT FRUIT — robot automat de trading F&V pe baza ofertelor primite in email. Coordoneaza fv-trader + fv-dealer + 4 skills (fv-email-poller, fv-offer-extractor, fv-price-book, fv-deal-flow). Use cand utilizatorul cere 'ruleaza trading robot', 'run F&V cycle', 'verifica oferte noi', 'fa price book', 'match buyers', 'status trading', 'ce oferte avem', 'trading robot status', 'ruleaza ciclu complet', 'pipeline F&V'. Use si pentru re-runs: 're-executa extractie', 'regenereaza price book', 'reproceseaza ofertele'. Orice cerere in directorul TRADING ROBOT FRUIT/."
---

# Skill: fv-trading-orchestrator

**Executie:** sub-agent (fv-trader ca operator principal, fv-dealer la nevoie,
fv-fb-publisher pentru postari Facebook — gated).

**Cand se foloseste:** orice cerere in TRADING ROBOT FRUIT/, sau orice cerere
de "trading F&V", "robot oferte", "price book legume-fructe".

## Faze

### Phase 0: Context Check
- Exista `DATA/offers_ledger.jsonl`? Daca nu, initiaza cu structura goala
- Exista `DATA/price_book.json`? Daca nu, sau `--rebuild`: reconstruieste
- Exista `DATA/buyers_list.csv`? incearca sa populeze din COOP leads existente
- Verifica batch ID curent: daca acelasi batch exista, skip

### Phase 1: Poll Email (fv-email-poller + fv-inbox-cumparlegume)
```
fv-trader → fv-email-poller skill        → Yahoo apaminerala@yahoo.com
fv-trader → fv-inbox-cumparlegume skill  → cumparlegume@gmail.com (+ replici office@)
```
- Default: ultimele 7 zile (cumparlegume default 30)
- Parametri: `--days N` optional
- Output: lista emailuri F&V, salveaza raw in `DATA/raw_emails/`
- Ambele read-only; raspunsurile la COOP_EXPORT cad pe Gmail-ul cumparlegume

### Phase 2: Extract Offers (fv-offer-extractor)
```
fv-trader → fv-offer-extractor skill → parseaza emailuri → produce offers_ledger
```
- Pentru fiecare email nou: extrage produse structurate
- Scrie in `DATA/offers_ledger.jsonl` (append)
- Identifica oferte "partial" vs "complete"

### Phase 3: Update Price Book (fv-price-book)
```
fv-trader → fv-price-book skill → actualizeaza benchmark
```
- Reconstruieste price_book.json din offers_ledger
- Calculeaza benchmark, trend, EU market comparison
- Marcheaza low_confidence acolo unde e cazul

### Phase 4: Match Buyers (fv-deal-flow)
```
fv-trader → fv-deal-flow skill → match oferte cu cumparatori
```
- Incruciseaza offers_ledger cu buyers_list + requests_ledger
- Calculeaza match score
- Deschide dealuri pentru score >= 80%
- Listeaza potentiale (60-79%) pentru aprobare

### Phase 5: Publish social (FB + Telegram) — gated
```
fv-fb-publisher       → fv-fb-publish skill       → pagina FB Cumpar Legume (Graph API)
fv-telegram-publisher → fv-telegram-publish skill → canal @cumparlegume (Bot API)
```
- ACELASI anunt ASCII (OFERIM + CUMPARAM), fara preturi, exclude internal_only
- Fiecare canal: dedup pe continut (fb_post_log.json / tg_post_log.json) + cap 1/zi
- Health-check (GET /me | getMe) inainte de POST; **dry-run default, live DOAR cu aprobare**

### Phase 6: Report
```
fv-trader → raport numerotat Tudor
```
1. Oferte noi in batch: N (M complete, P partial)
2. Price book: X produse actualizate, Y cu trend semnificativ
3. Match-uri: Z noi (K dealuri deschise, L potentiale)
4. Dealuri active: W in negociere, V stalled
5. Probleme: erori IMAP, parsing failures, buyers fara email

## Re-runs / Partial Runs
| Comanda | Executie |
|---------|----------|
| "re-extract offers" | Phase 2 only |
| "rebuild price book" | Phase 3 only |
| "match again" | Phase 4 only |
| "run full cycle" | Phase 1→2→3→4→5 |
| "status trading" | Phase 5 only |
| "force poll" | Phase 1 cu --days 30 |

## Reguli
- Output numerotat, fara preambul
- Email ASCII-only (drafturi, send gated)
- Fara commit/push fara aprobare
- Leads keyed pe email non-null
- Daca o faza esueaza: logheaza, continua cu urmatoarea, raporteaza eroarea

## Test Scenarios
1. **Normal flow:** "ruleaza trading robot" → poll 3 emailuri → extrage 5 oferte → price book 3 produse → match 1 buyer → deal proposed
2. **Partial data:** email contine doar "ofer 5 tone mere" fara pret → extrage partial → price book low_confidence → match doar potential
3. **No new offers:** niciun email nou cu F&V → raporteaza "0 oferte noi, totul actual"

## Referinte
- `offers-memory-responder` — offers_ledger, auto_matcher, deal_broker (codul existent)
- `yahoo-imap-reader` — infrastructura IMAP Yahoo
- `COOP GOSPODARII DE ALTADATA/DATA/` — buyers_list, OP legume, cumparatori
