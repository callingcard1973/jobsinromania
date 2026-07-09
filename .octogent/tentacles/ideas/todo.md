# Todo

## Session 2026-04-23 06:48
## OIPA.RO Session 2026-04-23\n\n### Done\n- Fetched oipa.ro site (WP, natural-herbs-lite theme, gazduire.ro hosting)\n- Built membership signup page: inscriere-membri.php (standalone) + template-inscriere-membri.php (WP template)\n- Created oipa-inscriere-shortcode.php as mu-plugin via Claude API (oipa-claude-2026-xK9mP2vL)\n- Created WP page ID 9522 at https://oipa.ro/inscriere-membri/ with [oipa_inscriere] shortcode\n- Form: tip entitate radio cards, 41 judete dropdown, contact fields, produse/suprafata, mesaj\n- Submit: wp_mail() to contact@oipa.ro + auto-confirm to applicant\n- Verified: 19 HTML hits on live page = form rendering correctly\n\n### Key Files\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/CODE/inscriere-membri.php (standalone, unused)\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/CODE/template-inscriere-membri.php (WP template, uploaded to theme)\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/CODE/oipa-inscriere-shortcode.php (mu-plugin, ACTIVE)\n- Remote: /home/uamkawbd/oipa.ro/wp-content/mu-plugins/oipa-inscriere-shortcode.php\n\n### Hosting\n- Host: grem01.gazduire.ro:2083, user: uamkawbd\n- WP creds: apaminerala@yahoo.com / jgWJoxwgvXYlfxCFMZhUS7Cm\n- Claude API key on site: oipa-claude-2026-xK9mP2vL\n\n### Pending\n- Add inscriere-membri link to WP nav menu\n- Consider logging submissions to DB or Google Sheets\n- /remote-control skill not found - user may want to set it up

## Session 2026-04-24 02:46
## OIPA.RO Session 2026-04-23 (cont)\n\n### Done\n- Salvat 12 propuneri articole Tudor Seicarescu → articole-propuse.md\n- Fetchat CBI market intelligence pentru 7 produse (tomate, ardei, ceapă, căpșuni, mere, afine, fasole verde)\n- Inventariat 4 PDF-uri CBI existente pe hard (2015-2016) la D:/MEMORY/DATA/HAMBARUL ROMANESC/.../CBI Market info/\n- Salvat tot în cbi-market-intelligence.md\n\n### Pending\n- Descărcat PDFs de pe cbi.eu (agent a eșuat cu internal error)\n- Rescris articolele propuse în RO cu info din CBI integrată\n\n### Key Files\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/articole-propuse.md\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/cbi-market-intelligence.md\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/DATA/CBI/ (dir creat, gol)\n\n### Next\n- Retry descărcare PDFs CBI manual cu curl\n- Rescrie articolele propuse în RO cu date concrete din CBI

## Session 2026-04-24 02:59
## OIPA.RO Session 2026-04-23 (final)\n\n### Done\n- 14 PDF-uri CBI descărcate via raspibig → SCP laptop → D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/DATA/CBI/\n- 12 articole rescrise în română cu date CBI integrate → articole-cu-date-cbi.md\n- Articole originale (fără date) → articole-propuse.md\n\n### Key Files\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/articole-propuse.md — 12 titluri propuse\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/articole-cu-date-cbi.md — 12 articole complete RO cu date CBI\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/cbi-market-intelligence.md — index CBI intelligence\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/DATA/CBI/ — 14 PDF-uri (tomate, ardei, ceapă, căpșuni, afine, fasole verde, mere)\n\n### Pending\n- Mai multe produse CBI de descărcat (aubergine, peas, culinary-herbs, watermelons, table-grapes, plums)\n- Publicare articole pe WP (Tudor nu vrea deocamdată)\n- Adăugare link inscriere-membri în nav menu WP oipa.ro

## Session 2026-04-24 03:00
## OIPA.RO — handoff complet 2026-04-23\n\n### Livrat\n- Pagina inscriere membri LIVE: https://oipa.ro/inscriere-membri/ (WP page ID 9522, shortcode [oipa_inscriere])\n- mu-plugin: /home/uamkawbd/oipa.ro/wp-content/mu-plugins/oipa-inscriere-shortcode.php\n- 12 articole propuse + rescrise RO cu date CBI → articole-cu-date-cbi.md\n- 14 PDF-uri CBI descărcate → D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/DATA/CBI/\n- Index CBI intelligence → cbi-market-intelligence.md\n\n### Pending\n- Link inscriere-membri în nav menu WP\n- Descărcat restul CBI (aubergine, peas, culinary-herbs, watermelons, table-grapes, plums)\n- Publicare articole pe WP (pe hold)\n\n### Credențiale\n- Hosting: grem01.gazduire.ro:2083, user: uamkawbd, pass în D:/MEMORY/BUSINESS/OIPA/.env\n- WP: apaminerala@yahoo.com, pass în .env\n- Claude API key pe site: oipa-claude-2026-xK9mP2vL

## Session 2026-04-24 05:30

### Done
- Inspectat 164 idei din MASTER.csv — gasit 2 directoare noi fara IDEA: ISCIR + AGRO MAGAZIN
- Adaugat IDEA-163 (ISCIR scraper), IDEA-164 (Agro Magazin), IDEA-165 (WooCommerce shop), IDEA-166 (CIFN Data Platform)
- Analizat piata RO date companii: Termene (265K/luna), ListaFirme (687K/luna), RisCo (€0.2/query), Targetare (212K/luna), Confidas (€199-4999/an)
- Gasit nisa libera: date EU cross-border — nimeni nu are TED 18 tari + procurement + recrutare
- LemonSqueezy: verificat cont activ carteledeapel@gmail.com, store "Data Driven Lemon" ID 344296 GBP, API key nou salvat in .env
- Creat ghid upload HTML interactiv: GUMROAD_UPLOAD/ls_upload_guide.html — 19 produse cu copy-paste si checkbox progres
- Creat director CIFN_DATA_PLATFORM cu business plan complet (DOCS/business_plan.md)
- Inspectat cifn.eu: WP activ, blog fonduri europene 21 articole, PostHog instalat
- Decis arhitectura: cifn.eu/date/ sectiune noua standalone pe A2, API FastAPI pe raspibig port 7740
- Scris FastAPI API (main.py): endpoint /v1/firma/{cui} + /v1/search, rate limiting, JWT, free vs pro tier
- Scris frontend PHP (index.php): landing + CUI search + pricing page complet
- Verificat DB raspibig: 4.1M firme onrc_status, 184K datornici_anaf, 715K companies RO

### Pending — NEXT SESSION
- DECIZIE NECESARA: cum conectam A2 frontend → raspibig API
  - Optiunea recomandata: nginx pe raspibig cu subdomain api.cifn.eu + Bearer token + HTTPS
  - A2 shared hosting nu suporta SSH tunnel
- Deploy actual: SCP api/ pe raspibig, systemd service, nginx config
- Deploy frontend: SCP index.php pe A2 la ~/cifn.eu/date/
- LemonSqueezy: switch din test_mode la LIVE, upload manual 19 produse (ghid gata)

### Key Files
- D:/MEMORY/BUSINESS/IDEAS/CIFN_DATA_PLATFORM/CODE/api/main.py — FastAPI backend
- D:/MEMORY/BUSINESS/IDEAS/CIFN_DATA_PLATFORM/CODE/frontend/index.php — PHP frontend
- D:/MEMORY/BUSINESS/IDEAS/CIFN_DATA_PLATFORM/CODE/deploy.sh — deploy script (partial)
- D:/MEMORY/BUSINESS/IDEAS/CIFN_DATA_PLATFORM/DOCS/business_plan.md — plan complet
- D:/MEMORY/BUSINESS/IDEAS/GUMROAD_UPLOAD/ls_upload_guide.html — ghid upload LS
- D:/MEMORY/BUSINESS/IDEAS/GUMROAD_UPLOAD/.env — LS API key valid

### Credentials
- LemonSqueezy: carteledeapel@gmail.com, store 344296, API key in .env
- raspibig: tudor@192.168.100.21, DB interjob_master, API la port 7740 (de instalat)
- A2: loaiidil@nl1-cl8-ats1.a2hosting.com, docroot ~/cifn.eu/

## Session 2026-04-24 03:18
## OIPA.RO — save final 2026-04-23\n\n### Livrat complet\n- oipa.ro/inscriere-membri/ LIVE (WP page + mu-plugin)\n- 12 articole Tudor Seicarescu / OIPA cu date CBI integrate\n- 14 PDF-uri CBI descărcate (tomate/ardei/ceapă/căpșuni/afine/fasole/mere)\n\n### Fișiere cheie\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/articole-cu-date-cbi.md\n- D:/MEMORY/BUSINESS/IDEAS/OIPA.RO/DATA/CBI/ (14 PDFs)\n- D:/MEMORY/BUSINESS/TUDOR SEICARESCU LIFE STRATEGY/ARTICOLE OIPA/ (copie articole + CBI)\n\n### Pending\n- Nav menu WP: adăugat link inscriere-membri\n- CBI produse lipsă: aubergine, peas, culinary-herbs, watermelons, table-grapes, plums\n- Publicare articole pe WP (pe hold la cererea lui Tudor)

## Session 2026-04-25 02:58
## Session 2026-04-25 — America Import Business Research\n\n### Done\n- Creat CLAUDE.md in D:/MEMORY/BUSINESS/IDEAS/AMERICA/ cu scope + context business import SUA→EU\n- Studiat profilul Tudor: 166+ idei, infra email 6300/zi, 28K contacte HORECA, 28 domenii, agroevolution.com cu 9658 fermieri\n- Cercetat 4 directii de business import american in Europa:\n\n### Rezultate cercetare\n\n1. **Suplimente US → distribuitor RO/EU**\n   - Piata EU: 5.75B (2025), CAGR 7%\n   - NOW Foods are pagina aplicatie distribuitor: nowfoods.com/about-now/international/become-distributor\n   - Thorne: Romania neacoperita = oportunitate\n   - Notificare ANSVSA obligatorie per produs, VAT 11%\n   - Capital start: EUR 5-15K, marja 50-120%\n\n2. **Bourbon craft US → HORECA RO** (RECOMANDAT START RAPID)\n   - US whiskey exports EU: 99M in 2024 (+60% din 2021)\n   - Bourbon exclus din tarife represalii EU (confirmat April 2025)\n   - Craft distilleries US in criza supraproductie = disperate dupa distribuitori EU\n   - Canal existent: 28K contacte HORECA Tudor\n   - Capital start: EUR 15-40K, marja 35-50%\n\n3. **Specialty food (sauces/BBQ) → HORECA**\n   - Hot sauce market: .3B (2024) → B (2032)\n   - Model referinta: Crevel Europe GmbH (450 clienti, 28 tari, 560 tone/luna)\n   - Poate cumpara de la Crevel ca reseller fara import direct\n   - Capital start: EUR 3-10K, zero licente speciale\n\n4. **Master franchise US brand → RO/CEE** — ELIMINAT (capital EUR 200K+)\n\n### Strategie recomandata\n- Pas 1: Specialty food via Crevel Europe (zero bariere, stoc mic, canal HORECA gata)\n- Pas 2: Bourbon craft (licenta accize ~30 zile)\n- Pas 3: Suplimente track separat pe termen lung\n\n### Key files\n- D:/MEMORY/BUSINESS/IDEAS/AMERICA/CLAUDE.md\n\n### Pending\n- Tudor sa decida cu ce directie incepe\n- Daca specialty food: contactat Crevel Europe pentru conditii wholesale\n- Daca bourbon: deschis procedura accize ANAF + identificat 3-5 craft distilleries US
