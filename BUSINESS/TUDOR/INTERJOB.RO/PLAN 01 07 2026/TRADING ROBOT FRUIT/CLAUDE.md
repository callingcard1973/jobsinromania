# CLAUDE.md — TRADING ROBOT FRUIT

**Iulie 2026** · Robot automat de trading agro pe baza ofertelor din email.

## EVALUARE: 7 versiuni grain coexista pe raspibig (2026-07-11)

Am 7 locatii cu cod grain/trading pe .21, fiecare scris de un
context/tool/sesiune diferita. Scop: testez in paralel ca sa decid care
e cea mai simpla si potrivita pentru ce am eu nevoie. Nimic nu se
sterge sau suprascrie pana la decizie.

Detalii in `OPENCODE TRADING ROBOT/CLAUDE.md` sectiunea EVALUARE.

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
- **Sync ledger (HARD, 2026-07-10): RASPIBIG = sursa canonica** pentru
  `offers_ledger.jsonl` / `price_book.json` / `deals.jsonl` (poller cron 07:30 +
  publish 08:00 scriu pe .21). Laptopul e mirror **pull-only**:
  `CODE/pull_ledger_from_raspibig.ps1` (backup local `.bak_<data>` inainte de
  suprascriere). `push_ledger_to_raspibig.sh` RETRAS (one-way overwrite
  laptop->raspibig, risca sa stearga date scrise de cron) — arhivat in
  `CODE/_ARCHIVE/push_ledger_to_raspibig.sh.retired_20260710`. Nu impinge
  niciodata ledger-ul de pe laptop peste .21.

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
| 2026-07-01 | **`fv_to_publishing_robot.py`** — bridge TRADING_ROBOT -> PUBLISHING_ROBOT: citeste ledger, construieste post public (fara email/telefon/nume individuali, pastreaza doar `office@cumparlegume.com`), trimite la POST /inbox. Dry-run default; --post trimite efectiv. |
| 2026-07-01 | **Regula HARD:** Nu se publica NICIODATA date de contact individuale (email/telefon/nume furnizori sau cumparatori) pe canalele publice. `office@cumparlegume.com` este singurul contact permis in postari. Contactele individuale raman doar in ledger-ul privat. |
| 2026-07-01 | PUBLISHING_ROBOT **V2 multi-business**: `publish_configs/` cu config per business (cumparlegume.json, expats.json). Connectorii accepta `business="default|cumparlegume|expats"`, inbox accepta `business` field, workerul foloseste configul corect. Backward-compatibil (default=cumparlegume). |
| 2026-07-01 | Bridge nou: **`CODE/expats_to_robot.py`** — citeste continut de la stdin/fisier, strip_contacts, trimite la /inbox cu business=expats. Dry-run default. |
| 2026-07-01 | Skill nou: **`.claude/skills/publishing-robot/`** — documenteaza arhitectura multi-business PUBLISHING_ROBOT. |
| 2026-07-01 | **Expats in Romania** — config partial functional: WP (expatsinromania.org) merge. FB token expirat (pagina 288102411055455). TG bot (8754219480:AAH9...) nu e admin pe canal. De reparat: refresh FB token, adauga botul ca admin pe @expatsinromania_news.
| 2026-07-09 | **Harness: Cereal Deployment** — Agent team (deployment-orchestrator, ssh-ops-agent, python-env-agent, database-agent, service-agent, verification-agent) + skill (cereal-deployment-orchestrator) pentru deployment pe raspibig. raspibig este singurul server permanent online, operare autonoma. | |
| 2026-07-10 | Sync ledger INVERSAT: raspibig canonic, laptop pull-only (`CODE/pull_ledger_from_raspibig.ps1`); `push_ledger_to_raspibig.sh` retras in `CODE/_ARCHIVE/`. Reconciliere cod .21: `fv_offer_extractor.py` (UPDATE unificat + PG-WARN logging) deployat pe raspibig cu backup `.bak_20260710`; `fv_deal_flow.py` deja identic. py_compile + --help OK pe .21. |
| 2026-07-10 | **GRAIN DESK v1 LIVE** (aprobat Tudor): radar cereale timp-real in `/opt/ACTIVE/TRADING_ROBOT_FRUIT/GRAIN_DESK_CLAUDE/` (spatiu separat Claude, bloc crontab `# --- CLAUDE GRAIN DESK ---`). Poller 07:30 -> benchmark Agrointel zilnic 07:40 (DAP Constanta) -> `grain_deal_detector.py` la 15 min cu Telegram LIVE. N1=orice oferta; N2=-3% vs benchmark REGIONAL sau >=500t; N3=draft gated. Fara scoruri. + `anaf_pma_extract.py` (317 randuri/33 judete, cron luni 07:00) + `grain_backfill_archive.py` (gated). Cunostinte trader salvate in `.claude/agents/cereal-trader.md`. Canonic: TRADING=semnal, SILOZURI=contact (`../CEREALE_CANONICAL.md`). |
| 2026-07-11 | **OPENCODE TRADING ROBOT** — cod refactorizat doua desk-uri distincte (FV/CODE + GRAIN), buyer matcheri separati fara scoruri. Evaluare: 7 versiuni de cod grain coexistente pe raspibig (OPENCODE, Claude, Devin, legacy, systemd), nimic nu se suprascrie. Vezi `OPENCODE TRADING ROBOT/CLAUDE.md` sectiunea EVALUARE. |
