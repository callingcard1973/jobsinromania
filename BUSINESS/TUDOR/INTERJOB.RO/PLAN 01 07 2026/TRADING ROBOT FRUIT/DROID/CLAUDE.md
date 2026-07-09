# CLAUDE.md — TRADING ROBOT FRUIT

**Iulie 2026** · Robot automat de trading agro pe baza ofertelor din email.

## Harness: Trading Robot (legume + fructe + CEREALE)

**Scop:** Desk unic de trading agro. Cereale si legume-fructe sunt ACELASI
sistem (acelasi ledger, price book, matcher) — nu se separa. Citeste inboxuri,
extrage produse structurate (orice produs agro), mentine price book viu,
match-uieste cumparatori, track dealuri.

**Input:** Inboxuri (read-only):
- `apaminerala@yahoo.com` (Yahoo) — furnizori F&V + cereale
- `cumparlegume@gmail.com` (Gmail) — replici la campaniile COOP_EXPORT (F&V) si
  cereale (silozuri); aici cad raspunsurile la `office@cumparlegume.com`

**Produse:** legume, fructe, cereale (grau/orz/porumb/naut/floarea-soarelui etc).
Un singur `offers_ledger` le tine pe toate.

**Bazine de cumparatori:**
- F&V / conserve: `requests_ledger` (262 fabrici conserve) + buyers_list
- Cereale: 7.934 comercianti (`COOP/.../DATE_cereal_buyers_demand.csv`, CAEN 4621)

**Output:** offers_ledger, price_book, matched deals, rapoarte.

**Trigger:** Orice cerere despre trading F&V, oferte, price book, matching,
sau lucru in directorul TRADING ROBOT FRUIT/ — foloseste `fv-trading-orchestrator`.

**Structura:**
```
TRADING ROBOT FRUIT/
├── CLAUDE.md                 <- acest fisier
├── CODE/                     <- scripturi Python (fv_email_poller, fv_offer_extractor, fv_price_book, fv_deal_flow)
├── DATA/                     <- offers_ledger, price_book, deals, raw_emails, configuri API
├── PUBLISHING_ROBOT/         <- sistem publicare multi-canal cu aprobare Telegram (nou)
│   ├── publish_db.py         <- SQLite queue + publish_log
│   ├── publish_inbox.py      <- FastAPI POST /inbox (primeste de la AI)
│   ├── publish_bot.py        <- Bot Telegram cu butoane Aproba/Respinge/Editeaza/Programeaza
│   ├── publish_worker.py     <- Daemon: preia approved -> publica pe canale -> salveaza URL-uri
│   ├── publish_config.json   <- Token bot + chat_id (gitignored)
│   ├── publish_queue.db      <- SQLite (generat)
│   └── connectors/           <- Conectori independenti (reusesc configurile din DATA/)
│       ├── telegram.py       <- Publica pe canalul @cumparlegume
│       ├── wordpress.py      <- Publica pe cumparlegume.com (WP REST)
│       ├── facebook.py       <- Publica pe pagina FB Cumpar Legume (Graph API)
│       ├── linkedin.py       <- Stub
│       └── x.py              <- Stub
└── .claude/
    ├── agents/
    │   ├── fv-trader.md       <- operator principal
    │   └── fv-dealer.md       <- negociator automat
    └── skills/
        ├── fv-email-poller/
        ├── fv-offer-extractor/
        ├── fv-price-book/
        ├── fv-deal-flow/
        └── fv-trading-orchestrator/
```

**Detalii in `OPENCODE TRADING ROBOT` (raportul de constructie).**

## Reguli
- Output numerotat. Romana. Email ASCII-only.
- Fara commit/push/send fara aprobare explicita.
- Leads keyed pe email non-null.
- Integrare DNC unificat (dashboard 8096).
- Acest robot e pentru DIRECTIA 1 (COOP GOSPODARII DE ALTADATA) — aprovizionare F&V.

## Change log
| Data | Schimbare |
|------|-----------|
| 2026-06-28 | Initial scaffold: 2 agents + 5 skills + orchestrator + 4 CODE scripts |
| 2026-06-30 | FB publish portat din harness InterJob PUBLISHING IN MY FB: agent `fv-fb-publisher` + skill `fv-fb-publish` + `CODE/fv_fb_publisher.py` (curate->dedup->gate->post->token-health). Cablat ca Phase 5 in orchestrator. |
| 2026-07-01 | UNIFIED publish `fv_publish_all.py`: acelasi anunt pe FB+Telegram+WP dintr-o comanda (dedup per canal, gated, --only/--force). LIVE verificat pe toate 3. DEPLOY pe raspibig `/opt/ACTIVE/TRADING_ROBOT_FRUIT/` + cron zilnic 08:00. Sync ledger via `push_ledger_to_raspibig.sh` (ruleaza fv-trader dupa update). Agent `fv-telegram-publisher` + skill `fv-telegram-publish` cablate, Phase 5 orchestrator = FB+TG. |
| 2026-07-01 | Telegram publisher `fv_telegram_publisher.py` (oglinda FB) LIVE pe canalul public @cumparlegume via @cumparlegume_bot (token in DATA/telegram_cumparlegume.json gitignored). Acelasi build_post + curate/dedup/cap/gate. |
| 2026-07-01 | `fv_fb_publisher.py` simplificat la Graph-only (234->124 linii); WP/Blog2Social/Make scoase (Graph merge ca joburile). Postare FB LIVE verificata pe pagina. |
| 2026-07-01 | 3 rute de publicare in `fv_fb_publisher.py`: (0) WP REST -> Blog2Social cross-posteaza pe FB [ALES], (1) Make webhook, (2) Graph API token. cumparlegume.com = WP 6.9.4, Application Passwords ON. LIVE: articol de test id=2365 publicat via WP REST (user `cumparlegume`, app-pw in config gitignored). RAMANE de verificat ca Blog2Social chiar declanseaza cross-post pe FB la articole create prin REST. |
| 2026-07-01 | **PUBLISHING_ROBOT** construit: `publish_db.py` (SQLite), `publish_inbox.py` (FastAPI POST /inbox), `publish_bot.py` (Telegram cu butoane Aproba/Respinge/Editeaza/Programeaza + callback handler), `publish_worker.py` (daemon publicare), 5 conectori (`telegram.py`, `wordpress.py`, `facebook.py`, `linkedin.py`, `x.py`). Flux: AI -> inbox -> pending -> TG preview -> Aproba -> worker -> URL-uri. Connectorii reusesc configurile din `DATA/`. |
