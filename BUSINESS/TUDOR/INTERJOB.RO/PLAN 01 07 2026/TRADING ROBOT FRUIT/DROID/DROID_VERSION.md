# DROID version - Trading Robot Fruit (self-contained snapshot)

Snapshot self-contained al robotului de trading F&V, versiunea reparata de Droid.
Ruleaza fara dependinte din foldere parinte. DATA/ este gitignored (contine PII + tokenuri).

## Structura
- CODE/            pipeline fv_* + modul offers-memory (requests_ledger, offers_ledger,
                   auto_matcher, deal_broker, offers_responder) + legume_taxonomy + templates/
- PUBLISHING_ROBOT/ publicare multi-canal (publish_db/inbox/bot/worker) + connectors/ (doar cod)
- .claude/         harness: 4 agenti + 8 skills (orchestrator fv-trading)
- DATA/            ledgere, CSV, drafts, raw_emails, configuri API (gitignored)
- root: trading_robot.py, mega_image_imap_fetch.py, mega_image_price_memory.py,
        ingest_fabrici_conserve.py + docs (CLAUDE.md, README.md, PROCEDURA.md, HANDOFF)

## Cum rulezi (din DROID/)
- Price book:      python CODE/fv_price_book.py
- Match oferte:    python CODE/fv_deal_flow.py --match
- Match cereri:    python CODE/fv_request_supplier_matcher.py
- Ciclu complet:   python CODE/fv_trading_runner.py --password <YAHOO_APP_PW>
- Ingest fabrici:  python ingest_fabrici_conserve.py
- Mega Image IMAP: set YAHOO_APAMINERALA_APP_PASSWORD apoi python mega_image_imap_fetch.py
- Publicare:       python CODE/fv_publish_all.py [--post] [--only fb,tg,wp] [--force]

## Env / secrete (nu sunt hardcodate)
- YAHOO_APAMINERALA_APP_PASSWORD  (mega_image_imap_fetch, fail-closed)
- fv poller: parola Yahoo/Gmail via --password
- DATA/fb_cumparlegume.json (FB token + WP app-pw), DATA/telegram_cumparlegume.json (bot token)

## Ce a fost reparat in aceasta versiune
1. Secrete: eliminat app-password Yahoo hardcodat (fail-closed); .gitignore ignora *.sh + HANDOFF_*.md.
2. fv_email_poller: cautare IMAP SINCE (inainte: fraza multi-keyword = 0 rezultate); guard None-payload;
   supplier_email via parseaddr; set O(1) de id-uri procesate (inainte: re-citea tot ledgerul per mesaj).
3. fv_offer_extractor: fix typos regex ARDEI/VARZA; guard fals-match tone ('10 tomate', '5 to 10');
   normalizare taxonomy-first + colaps alias; thread supplier_email.
4. fv_deal_flow: identitate furnizor in dedup + deals prin constanta unica SUPPLIER_UNKNOWN
   (inainte: email_unknown vs via_email_offer => dedup mort); set chei deal active; scriere atomica.
5. fv_request_supplier_matcher + trading_robot: legume_taxonomy local unic; round-robin deprecat.

## Self-containment
- Importurile modulului offers-memory si ingest repointate la CODE/ + DATA/ locale.
- requests_ledger/offers_ledger scriu in DATA/00_SHARED_leads_si_dnc/ (local, distinct de ledgerul fv).

## Caveat (dependinte externe, needuse in pachet)
- trading_robot.py (DEPRECAT) si construieste_suppliers_master.py citesc CSV-uri sursa mari,
  scrappate, din afara robotului (via_profi_producers..., COOP GOSPODARII). Acelea sunt feed-uri
  upstream de date, nu cod; nu sunt incluse. Restul codului ruleaza self-contained.

## Verificare (toate verzi)
py_compile pe tot .py = OK; fv_price_book=5 produse; fv_deal_flow --match=3; matcher=47/32 ready;
ingest_fabrici_conserve=262 fabrici scrise in DROID/DATA (fara acces la parinte).
