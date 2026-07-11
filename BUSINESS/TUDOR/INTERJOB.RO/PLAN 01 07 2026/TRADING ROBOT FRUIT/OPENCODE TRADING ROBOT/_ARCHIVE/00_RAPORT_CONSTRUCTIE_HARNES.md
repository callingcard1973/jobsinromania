# RAPORT CONSTRUCTIE — Trading Robot F&V

**Data:** 2026-06-28
**Director:** TRADING ROBOT FRUIT/
**Context:** Directia 1 (COOP GOSPODARII DE ALTADATA) — aprovizionare F&V automata

---

## Ce s-a construit

### Arhitectura

```
TRADING ROBOT FRUIT/
├── CLAUDE.md                   
├── CODE/                       
│   ├── fv_email_poller.py      <- pollare IMAP Yahoo (apaminerala@yahoo.com)
│   ├── fv_offer_extractor.py   <- parsat email -> oferte structurate
│   ├── fv_price_book.py        <- benchmark + trend per produs/calitate/origine
│   ├── fv_deal_flow.py         <- match cumparatori + deal lifecycle
│   └── fv_trading_runner.py    <- orchestrator runner (ciclu complet/partial)
├── DATA/                       
│   ├── offers_ledger.jsonl     <- registru oferte (append-only)
│   ├── price_book.json         <- benchmark preturi
│   ├── deals.jsonl             <- dealuri propuse
│   ├── buyers_list.csv         <- cumparatori (de populat)
│   └── raw_emails/             <- emailuri raw salvate
└── .claude/
    ├── agents/
    │   ├── fv-trader.md         <- operator principal
    │   └── fv-dealer.md         <- negociator automat
    └── skills/
        ├── fv-email-poller/
        ├── fv-offer-extractor/
        ├── fv-price-book/
        ├── fv-deal-flow/
        └── fv-trading-orchestrator/
```

### 2 Agenti
| Agent | Rol | Skills |
|-------|-----|--------|
| **fv-trader** | Opera ciclul: poll email → extract → price book → match → raport | toate 4 |
| **fv-dealer** | Gestioneaza negocierea dealurilor, drafturi, contra-oferte | deal-flow, price-book |

### 5 Skills
| Skill | Input | Output |
|-------|-------|--------|
| **fv-email-poller** | Yahoo IMAP (apaminerala@yahoo.com) | Lista emailuri F&V, raw in DATA/ |
| **fv-offer-extractor** | Raw email text | Oferte structurate in offers_ledger.jsonl |
| **fv-price-book** | offers_ledger.jsonl | price_book.json (benchmark per produs) |
| **fv-deal-flow** | Oferte + buyers_list | Match-uri, dealuri in deals.jsonl |
| **fv-trading-orchestrator** | Comenzi Tudor | Ruleaza fazele secvential |

### 5 Scripturi Python
| Script | Ce face |
|--------|---------|
| `fv_email_poller.py` | IMAP connect, F&V keyword filter, save raw, dedup |
| `fv_offer_extractor.py` | NLP regex: produs, cantitate, pret, calitate, origine, termeni |
| `fv_price_book.py` | Grupeaza, calculeaza min/max/avg/median/trend |
| `fv_deal_flow.py` | Match weighted (produs 40%, calitate 25%, pret 20%...), deal CRUD |
| `fv_trading_runner.py` | Runner unificat cu faze: poll→pricebook→matching→report |

### Date
- `DATA/offers_ledger.jsonl` — registru oferte (append JSONL)
- `DATA/price_book.json` — benchmark per (produs, calitate, origine)
- `DATA/deals.jsonl` — dealuri cu istoric
- `DATA/buyers_list.csv` — inca gol, de populat din COOP leads
- `DATA/raw_emails/` — emailuri raw salvate la poll

---

## Ce exista si se reutilizeaza din Iunie

| Resursa | Unde | Ce face |
|---------|------|---------|
| `yahoo-imap-reader` | `/opt/ACTIVE/SKILLS/` pe raspibig | Infrastructura IMAP Yahoo (app password, host) |
| `offers-memory-responder` | `PLAN 01 07 2026/.claude/skills/` | offers_ledger, auto_matcher, deal_broker |
| COOP buyers | `COOP GOSPODARII DE ALTADATA/DATA/` | Cumparatori din campania COOP_EXPORT |
| EU wholesale scrapers | `D:\MEMORY\SCRAPERS/scrapers/eu_wholesale/` | Preturi Rungis, Berlin, Madrid pt benchmark |
| DNC unificat | Dashboard 8096 | Suppression list |

---

## Cum se foloseste

```bash
# Ciclu complet (poll + extract + price book + match + report)
python CODE/fv_trading_runner.py --password APP_PASSWORD

# Doar price book (fara poll)
python CODE/fv_trading_runner.py --skip-poll --password X

# O singura faza
python CODE/fv_trading_runner.py --phase poll --password X
python CODE/fv_trading_runner.py --phase pricebook
python CODE/fv_trading_runner.py --phase matching
python CODE/fv_trading_runner.py --phase report

# Deal management
python CODE/fv_deal_flow.py --match
python CODE/fv_deal_flow.py --deals --summary
python CODE/fv_deal_flow.py --open-deal --offer-id <id> --buyer-email <email>
python CODE/fv_deal_flow.py --deals --status proposed

# Price book
python CODE/fv_price_book.py --rebuild
python CODE/fv_price_book.py --trends
python CODE/fv_price_book.py --product rosii
```

---

## Ce urmeaza (propuneri)
1. Populeaza `DATA/buyers_list.csv` din datele COOP existente
2. Primul test: `--phase poll` cu app password
3. Configureaza pe raspibig ca cron zilnic
4. Conecteaza matching-ul si la buyers din EU wholesale
5. Adauga alerta Telegram pentru dealuri ready (score >= 80%)
