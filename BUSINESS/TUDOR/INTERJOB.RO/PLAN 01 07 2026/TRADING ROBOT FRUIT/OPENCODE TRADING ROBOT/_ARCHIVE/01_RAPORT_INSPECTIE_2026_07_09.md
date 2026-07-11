# INSPECTIE — TRADING ROBOT FRUIT (2026-07-09)

**Raport salvat de:** opencode · **Director:** `TRADING ROBOT FRUIT/`
**Sursa comanda:** inspecție completă + raport în `OPENCODE TRADING ROBOT/`

---

## 1. STRUCTURĂ GENERALĂ (ce există)

```
TRADING ROBOT FRUIT/
├── CLAUDE.md, README.md, PROCEDURA.md, HANDOFF_2026_07_01.md, Harta_Publicare.md
├── CLAUDE TRADING ROBOT/        <- rapoarte + CSV-uri (matches, mega_image_price)
├── CODE/                         <- 61 scripturi .py (fv_*, cereale_*, mega_*, patch_*, fix_*)
│   └── desk_extensions/          <- eu_arbitrage, landed_price, pnl_tracker, supplier_reliability, grade_normalizer, demand_aggregator
├── DATA/                         <- offers_ledger.jsonl (44KB), price_book.json, raw_emails (40), drafts/, configuri gitignored
├── PUBLISHING_ROBOT/             <- publish_db/inbox/bot/worker + connectors/ + node_modules + whatsapp_session (browser cache)
├── .claude/                      <- 4 agenți + 10 skills (fv-* + publishing-robot)
├── DROID/                        <- SNAPSHOT self-contained (codul produs de Droid, păstrat)
└── OPENCODE TRADING ROBOT/       <- acest raport + 00_RAPORT_CONSTRUCTIE_HARNES.md
```

## 2. STARE LIVE (din HANDOFF 2026-07-01)

- **Publicare FB + Telegram + WP** LIVE verificată pe `cumparlegume` (posturi + articol `oferte-legume-fructe-2026-07-01`).
- **Deploy** pe raspibig `/opt/ACTIVE/TRADING_ROBOT_FRUIT/` + **cron 08:00** `fv_publish_all.py --post`.
- **Ledger sync** prin `CODE/push_ledger_to_raspibig.sh` (conține parolă SSH, negitat).
- **Fix ANOFM** aplicat (ij_jobs 14.009 → 7.990 joburi reale).
- **Polylang** scos de pe cumparlegume.com (articolul WP redirecta la home).
- Commit `35e5f9e` (nepush-at). Git repo local are 1 commit (`2a5a5d2` clean snapshot, secrete scrubate).

## 3. GIT STATUS

- `M CODE/fv_deal_flow.py`, `M CODE/fv_offer_extractor.py` — **modificări necomitate**.
- Restul arborizării este curată (DATA/ + HANDOFF_*.md + *.sh sunt gitignored).
- **Fără commit/push** (conform regulă HARD — așteaptă aprobare).

## 4. PROBLEME / CLUTTER (de curățat)

1. **`PUBLISHING_ROBOT/whatsapp_session/` = 448.6 MB** — browser Chromium user-data-dir (cache, GPU, LevelDB, hyphen, zod-WASM). **Gunoi, nu are ce căuta în repo.** Nu e gitignored. → șterge / adaugă în .gitignore.
2. **`PUBLISHING_ROBOT/connectors/node_modules/` = 65.6 MB** (zod v3/v4 + locale-uri). Nu e gitignored. → adaugă `node_modules/` în .gitignore sau șterge (e doar JS de conector).
3. **`DROID/`** = snapshot self-contained al lui Droid. Decis: **Droid abandonat** (nu se mai plătește), dar **codul se păstrează și se folosește**. Nu șterge — e arhivă de cod bun (23 .py, inclusiv `offers-memory` module, `auto_matcher`, `deal_broker`).
4. **Mulți `patch_*` / `fix_*` / `_*` scripturi** în CODE/ (ex: `patch_reply_wa.py`, `fix_reply_indent.py`, `fix_reply_wa_interest_only.py`, `_add_requests.py`, `_patch_digest_trading.py`). Probabil one-off-uri de corecție — verifică dacă mai sunt necesare sau arhivează.

## 5. OBSERVAȚII FUNCȚIONALE

- **Cereale**: pipeline separat dezvoltat (`cereale_intake.py`, `cereale_benchmark.py`, `cereale_landed_port.py`, `cereale_spread_alert.py`, `publish_cereale_tg.py`, `pregateste_cereale_outreach_bucket_B.py`, `CODA_cereale_bucket_B.csv` 10.6KB). Suprapunere cu SILOZURI (nota OPEN din plan) — de unificat sursa canonicală.
- **desk_extensions/**: arbitraj EU (`eu_arbitrage.py`, `landed_price.py`), `pnl_tracker.py`, `supplier_reliability.py`, `grade_normalizer.py`, `demand_aggregator.py` — modul de trading avansat, DB local `DATA/desk_extensions/desk_extensions.db`.
- **Mega Image**: `mega_image_imap_fetch.py` + `mega_image_price_memory.py` + CSV-uri de preț în `CLAUDE TRADING ROBOT/`.
- **Publishing robot**: multi-business (`publish_configs/cumparlegume.json`, `expats.json`); expats are FB token expirat + TG bot fără admin (din changelog).

## 6. RECOMANDĂRI (numerotate)

1. **Curăță `whatsapp_session/`** (448 MB) — șterge sau gitignore; e cache browser, nu cod.
2. **Gitignore `PUBLISHING_ROBOT/connectors/node_modules/`** (65 MB) — sau șterge dacă JS nu e rulat local.
3. **Commit modificările** `fv_deal_flow.py` + `fv_offer_extractor.py` (sau verifică diff-ul dacă nu le-ai făcut tu).
4. **Arhivează `patch_*`/`fix_*`** one-off-uri în CODE/ dacă nu mai sunt folosite în pipeline.
5. **Unifică pipeline cereale** TRADING ROBOT vs SILOZURI (evită dubla audiență).
6. **Păstrează `DROID/`** ca arhivă de cod (Droid abandonat, codul util) — eventual mută modulele `offers-memory`/matcher în CODE/ dacă le vrei canonice.
7. **Repară Expats publishing** (FB token + TG admin) dacă e încă prioritate.
