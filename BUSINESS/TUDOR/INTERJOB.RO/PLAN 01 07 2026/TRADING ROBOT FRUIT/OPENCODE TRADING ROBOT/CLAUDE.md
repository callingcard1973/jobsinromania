# CLAUDE.md — OPENCODE TRADING ROBOT

**Iulie 2026** · Robot de trading agro, doua birouri SEPARATE:
**F&V (legume-fructe)** si **CEREALE (cultura mare: grau, porumb, orz,
floarea-soarelui, rapita)**. Cod canonic aici; portat din DROID (claude) +
`TRADING ROBOT FRUIT/CODE` (cereale), refactorizat ca doua desk-uri distincte.

## EVALUARE: multiple versiuni de cod in paralel (2026-07-11)

Acest cod (`OPENCODE TRADING ROBOT/`) este UNA din versiunile in evaluare.
Pe **raspibig** exista 6 locatii cu cod grain/trading, fiecare scris de
context/tool diferit, cu structura si stil propriu:

| Cale (pe .21) | Sursa | Ce contine |
|---------------|-------|------------|
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/CODE/` | FV cron canonic | fv_email_poller, fv_offer_extractor, fv_publish_all, etc. |
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/GRAIN/` | OPENCODE (noi) | doar 4 buyer-matcher scripturi |
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/grain_opencode/` | OPENCODE (scratch) | pipeline + cereale_intake/benchmark/spread + config.py |
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/GRAIN_DESK_CLAUDE/` | Claude | grain_deal_detector, matif carry, dash, vessel lineup |
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/grain_devin/` | Devin | versiune Devin |
| `/opt/ACTIVE/TRADING_ROBOT_FRUIT/grain_legacy/` | old | versiune veche |
| `/opt/ACTIVE/CEREAL_TRADING_ROBOT/` | systemd services | cereal-*-fetcher, schema, CODE/ |

Toate sunt pastrate. Nimic nu se suprascrie sau sterge pana la decizia
finala Tudor. Modificarile din aceasta sesiune raman LOCAL + git.

## REGULA HARD: grain si fruit/veg sunt DIFERITE

Nu se amesteca. Tradeaza diferit:
- **F&V**: kg, wholesale local/export, fabrici conserve + lanturi → JSONL ledger.
- **Cereale**: tone, MATIF/Constanta FOB, silozuri/comercianti CAEN 4621 → PostgreSQL.

Fiecare desk are ledger/benchmark/buyers/publishing propriu. Runner-ul
(`trading_robot.py`) le ruleaza separat (`fv`, `grain`, `all`).

## Structura

```
OPENCODE TRADING ROBOT/
├── config.py                 <- paths + DB + inboxuri + resolve SILOZURI
├── trading_robot.py          <- runner unic: fv | grain | all | status
├── CLAUDE.md                 <- acest fisier
├── CODE/                     <- FV DESK (scripturi active)
│   ├── fv_email_poller.py    <- Yahoo/Gmail IMAP poll (read-only)
│   ├── fv_offer_extractor.py <- parse email -> offers_ledger.jsonl
│   ├── fv_price_book.py      <- benchmark F&V (price_book.json)
│   ├── fv_deal_flow.py       <- match oferte-cumparatori FV + deals
│   ├── fv_publish_all.py     <- FB+TG+WP (dry-run default)
│   ├── fv_fb_publisher.py    <- FB publisher (Graph API)
│   ├── fv_telegram_publisher.py <- TG publisher
│   ├── fv_trading_runner.py  <- ciclu complet FV
│   ├── legume_taxonomy.py    <- vocab F&V multilingv
│   ├── offers_ledger.py      <- offers_ledger.jsonl (append)
│   ├── requests_ledger.py    <- requests_ledger.jsonl
│   ├── offers_responder.py   <- pregateste raspunsuri ASCII
│   ├── templates/            <- template-uri email/mesaje
│   └── _LEGACY/              <- scripturi inlocuite (pastrate ca referinta)
├── GRAIN/                    <- CEREALE DESK
│   ├── cereale_intake.py     <- parse WA/SMS/email grau -> ledger (category=cereal)
│   ├── cereale_benchmark.py  <- MATIF/BRM/Constanta FOB/APIA -> cereale_price_benchmark
│   ├── cereale_spread_alert.py <- spread vs benchmark -> alert intern TG/WA
│   ├── publish_cereale_tg.py <- post pe canalul @cereale_romania (dry default)
│   ├── wa_inbound.py         <- HTTP receiver POST /inbound -> ledger + PG (auto-feed)
│   ├── wa_notify.py          <- notificari interne Tudor (WA)
│   ├── whatsapp_bridge.py    <- bridge WA
│   ├── grain_buyer_match.py  <- oferte cereale -> CAEN 4621 (fara scor)
│   ├── fv_buyer_match.py     <- oferte FV -> CAEN 4631 + fabrici conserve (fara scor)
│   ├── buyers.py             <- stub (redirect)
│   ├── buyer_match.py        <- stub (deprecated)
│   ├── cereale_landed_port.py<- calcul landed cost Constanta
│   ├── pregateste_cereale_outreach_bucket_B.py <- constructie lista B
│   ├── cereale_schema.sql    <- schema PG trading_offers
│   └── _PIPELINE/            <- scripturi one-time (enrich, extract, build buyers)
└── DATA/                     <- date + configuri (gitignored partial)
    ├── enriched_final.csv    <- baza cumparatori canonica (12.360 CUI)
    ├── telegram_cereale.json.template
    ├── whatsapp_internal.json.template
    └── _INTERMEDIATE/        <- fisiere intermediare de constructie
```

## Date / store

- **FV**: `DATA/offers_ledger.jsonl` (append JSONL) + `DATA/price_book.json`.
- **Cereale**: PostgreSQL `interjob_master` pe raspibig (192.168.100.21):
  - `trading_offers` (category='cereal')
  - `cereale_price_benchmark`, `cereale_spread_alerts`
  - Schema: parinte `trading_schema.sql` + `cereale_schema.sql` (aplica pe raspibig).

## Buyer base canonic (OPEN issue rezolvat)

- **SILOZURI** = sursa canonica buyer cereale: `SILOZURI/BUYERS/cereal_buyers_romania.csv`
  (~7.934 traderi CAEN 4621). TRADING ROBOT citeste asta, NU re-crawl-eaza.
- Regula: SILOZURI = outbound rece; TRADING ROBOT = match oferte INBOUND la aceiasi buyeri.
  Niciun lead trimis de doua ori. Vezi `GRAIN/buyers.py`.

## Flux grain (auto-feed WhatsApp)

```
WhatsApp inbound -> whatsapp-connector -> POST http://127.0.0.1:5524/inbound
  -> GRAIN/wa_inbound.py -> cereale_intake.ingest (parse) -> JSONL + PG trading_offers
  -> cereale_spread_alert (vs benchmark) -> alert intern Tudor (TG/WA, niciodata extern)
  -> publish_cereale_tg (post canal dedicat, dry default)
```
Hookup receive-side connector = pas de go-live (connectorul e azi send-only).

## Rulare

```bash
python trading_robot.py status            # ambele desk-uri
python trading_robot.py fv [--publish]    # F&V (dry default)
python trading_robot.py grain [--publish] # cereale (dry default)
python trading_robot.py all                # ambele separate

# grain manual / demo
python GRAIN/cereale_intake.py --demo
python GRAIN/cereale_intake.py --from-text "vand grau 300t 190 eur/to Constanta" --store
python GRAIN/wa_inbound.py --port 5524     # receiver auto-feed
python GRAIN/grain_buyer_match.py --csv    # match cereale -> CAEN 4621
python GRAIN/fv_buyer_match.py --json      # match FV -> CAEN 4631 + fabrici
python GRAIN/buyers.py report
```

## Deploy pe raspibig (regula Tudor)

- **Pentru fiecare "programare" (cron/scheduler) se tine o VERSIUNE SEPARATA** in
  `/opt/ACTIVE/TRADING_ROBOT_FRUIT/` — FV (08:00), grain benchmark+spread, grain
  TG publish, WA inbound receiver ruleaza ca procese/cron-uri distincte, fiecare
  cu propriul build/versiune, nu se suprascriu unul pe altul.

## Reguli (mostenite)

- Output numerotat, romana, ASCII-only.
- Fara commit/push/send fara aprobare explicita.
- Leads keyed pe email non-null; contacte individuale NICIODATA in public.
- Secrete in `DATA/*.json` (gitignored) — nu pe GitHub.
