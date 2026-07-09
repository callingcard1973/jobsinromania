# AIR TICKETS + TRAVEL RESELLING + EMAIL ENRICHMENT + 14 AGENTS — Handoff (2026-04-13)

## THE BIG NUMBERS
- **83M+** website URLs without email across DB + CSVs
- **331,564** master_emails (deduped, unique, growing daily)
- **+1,475,223** emails added this session (1.45M backfill + 21.8K scraping + 28 pipeline)
- **14 autonomous agents** on raspibig, zero tokens, 24/7
- **30 cron lines** covering every hour of the day
- **85K** tourism records downloaded (agencies + hotels)
- **100+** travel/flight APIs researched with signup URLs
- **1,448** IATA agencies in campaign DB, ready to send
- Full agent inventory: `AGENTS_INVENTORY.md`

## What Was Done

### Data
- **Downloaded** full SITUR list: 2,968 licensed Romanian travel agencies
- **Filtered** to 1,448 Organizatoare (IATA-accredited) with email
- **Imported** into PostgreSQL `interjob_master.flight_agencies_campaign` (1,448 rows, 1,435 unique emails)
- Files: `agentii_turistice_clean.csv` (all 2,968), `agentii_organizatoare_campaign.csv` (1,448 filtered)

### Campaign Infrastructure (on raspibig)
- **PostgreSQL tables created:**
  - `flight_agencies_campaign` — 1,448 contacts with indexes
  - `flight_agencies_send_log` — send tracking
  - `flight_prices` — price monitor data
- **Config deployed:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/flight_agencies.json`
  - Sector ORGANIZATOARE: 50/day, Brevo via expatsinromania.org, ENABLED
  - Sector ORGANIZATOARE_ONLINE: 30/day, same sender, DISABLED (enable when ready)
- **Template deployed:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/template1.txt`
  - Subject: "Parteneriat bilete avion — 6,300 muncitori/zi cauta zboruri"
  - Reply-to: manpower.dristor@gmail.com
- **Price monitor deployed:** `/opt/ACTIVE/FLIGHTS/price_monitor.py`
  - Monitors 10 ethnic routes (OTP-AMS, OTP-BER, KTM-OTP, etc.)
  - Stores to PostgreSQL, alerts on >15% price drops
  - **Needs:** Tequila API key OR Travelpayouts key in env

### Flight Search Page
- **Built:** `D:\MEMORY\AIR TICKETS\flights.html` (Kiwi Tequila API)
- **NOT deployed** to expatsinromania.org/flights/ yet — needs API key
- FTP creds: 209.124.66.6, raspibig@loaiidil.a2hosted.com
- Deploy path: /expatsinromania.org/flights/index.html

### Kiwi.com Outreach
- **Email sent** to affiliates@kiwi.com from Gmail (2026-04-12)
- Awaiting response (typically 2-5 business days)

### IATA Partner Research
- **Documented:** `IATA_PARTNERS_ROMANIA.md`
- Top targets: Paralela 45, Christian Tour, Paravion, Cocktail Holidays
- Legal: need tourism license if collecting payment, not needed for affiliate-only

### API Research
- **Documented:** `FLIGHT_APIs_RESEARCH.md`
- 15+ APIs/programs researched with signup URLs, commission rates
- Best instant options: Travelpayouts, Amadeus, Duffel
- Best airline affiliates: Wizz Air + Ryanair via Awin
- Best Romanian OTAs: Vola.ro + Paravion via Profitshare.ro

## What's NOT Done Yet

### Needs Tudor's Action — SIGNUPS (30 min total, unlocks everything)

**Day 1 — Instant:**
1. **Travelpayouts** — https://www.travelpayouts.com/registration (instant key, 100+ brands, API)
2. **eSKY Linker** — https://eskypartners.com (open, no approval, 20-40% commission)
3. **Amadeus** — https://developers.amadeus.com/register (free test, best search data)

**Day 1-2 — Quick approval:**
4. **CJ Affiliate** — https://www.cj.com (Turkish, Emirates, Qatar, Austrian, Cathay, CheapOair, JustFly, Priceline)
5. **Awin** — https://www.awin.com (Booking.com, eDreams, EasyJet, Etihad, CheapOair, Wizz Air)

**Week 1 — Apply within networks:**
6. Wizz Air (via Admitad/Sovrn)
7. Skyscanner (via Impact — partners.skyscanner.net)
8. KAYAK/Momondo (affiliates.kayak.com)
9. Omio (via Impact — omio.com/affiliate)

**Week 2:**
10. **Duffel** — https://app.duffel.com/join (sell tickets with own markup, highest margin)
4. **Approve email template** — see template in `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/template1.txt`
5. **Register Kiwi Tequila** — if they respond to affiliates@kiwi.com email

### Needs API Key to Complete
1. **Update flights.html** — replace `YOUR_API_KEY_HERE` with Travelpayouts or Kiwi key
2. **Deploy flights.html** to expatsinromania.org/flights/ via FTP
3. **Update price_monitor.py** env — set `TEQUILA_API_KEY` in `/opt/ACTIVE/EMAIL/CAMPAIGNS/.env`
4. **Add cron** for price monitor: `0 */6 * * * cd /opt/ACTIVE/FLIGHTS && /opt/ACTIVE/INFRA/venv/bin/python3 price_monitor.py >> /opt/ACTIVE/FLIGHTS/logs/cron.log 2>&1`

### Needs Approval to Launch
1. **Start campaign** — orchestrator already sees config, just needs Tudor's GO
2. **Enable ORGANIZATOARE_ONLINE sector** — currently disabled in config
3. **Add flight block to recruitment templates** — 3-line footer in constructii/transport/horeca templates

### WordPress Update
- Add "Flight Booking Service EUR 50" tier to expatsinromania.org/services/ (WP page ID 46878)

## CURRENTLY RUNNING (2026-04-12 19:00+)

| Job | Total | ETA | Output |
|-----|-------|-----|--------|
| OSM hotels email scrape | 9,651 | ~20:05 | `TOURISM_DATA/osm/osm_hotels_enriched.csv` |
| France hotels email scrape | 21,155 | ~24:00 | `TOURISM_DATA/france_hotels_enriched.csv` |
| Wikidata hotels email scrape | 30,000 | ~maine seara | `TOURISM_DATA/wikidata/wikidata_hotels_enriched.csv` |

All zero tokens, running on raspibig in background. Check with:
```bash
ssh tudor@192.168.100.21 'ps aux | grep scrape_email | grep -v grep | wc -l'
ssh tudor@192.168.100.21 'wc -l /opt/ACTIVE/FLIGHTS/TOURISM_DATA/*/enriched*.csv /opt/ACTIVE/FLIGHTS/TOURISM_DATA/*enriched*.csv 2>/dev/null'
```

When done, copy results local:
```bash
scp tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/TOURISM_DATA/osm/osm_hotels_enriched.csv "D:/MEMORY/AIR TICKETS/TOURISM_DATA/"
scp tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/TOURISM_DATA/france_hotels_enriched.csv "D:/MEMORY/AIR TICKETS/TOURISM_DATA/"
scp tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/TOURISM_DATA/wikidata/wikidata_hotels_enriched.csv "D:/MEMORY/AIR TICKETS/TOURISM_DATA/"
```

## EMAIL ENRICHMENT PIPELINE — AUTOMATED, STAGGERED NIGHTLY

5 cron jobs, ore diferite, fiecare noapte:

| Ora | Tabele | Script |
|-----|--------|--------|
| 21:00 | Romania (master_ro, onrc, agencies, flight_agencies) | `--tables master_romania_companies,...` |
| 22:00 | Nordics (NO, SE, DK, FI, NL) | `--tables no_companies_full,...` |
| 23:00 | Central+Sud EU (PL, CH, AT, HU, IT, ES) | `--tables pl_companies,...` |
| 00:30 | Big tables (companies_clean, contacts, ted, BE) | `--tables companies_clean,...` |
| 02:00 | Bulgaria | `--tables bg_business_catalog,...` |

**Script:** `/opt/ACTIVE/FLIGHTS/email_enrichment_pipeline.py`
**State:** `/opt/ACTIVE/FLIGHTS/enrichment/state.json` (remembers offset per table)
**Log:** `/opt/ACTIVE/FLIGHTS/logs/enrichment_cron.log`
**Batch:** 5,000 per table per night, 20 workers
**Total potential:** 9.4M CSV rows + millions in DB with website but no email

**Cron:** `0 23 * * *` pe raspibig
**Script:** `/opt/ACTIVE/FLIGHTS/email_enrichment_pipeline.py`
**What:** Scanez 19 DB tables, gasesc website fara email, scrapez, updatez DB
**Batch:** 5,000/tabel/noapte, 20 workeri
**State:** `/opt/ACTIVE/FLIGHTS/enrichment/state.json` (tine minte offset per tabel)
**Log:** `/opt/ACTIVE/FLIGHTS/logs/enrichment_cron.log`

9.4M rows in CSV-uri + milioane in DB cu website fara email. Pipeline-ul le proceseaza automat, noapte de noapte.

## EXPANDED: Full Travel Reselling (not just flights)

Beyond flights — tours, attractions, trains, buses, ferries, transfers, events, car rental, insurance, cruises. All documented in `TICKET_RESELLING_COMPLETE_LANDSCAPE.md`.

**Instant signups that cover EVERYTHING:**
1. **Travelpayouts** — flights+hotels+cars+tours+insurance (one dashboard)
2. **CJ Affiliate** — airlines+Ticketmaster+CruiseDirect+Allianz
3. **Awin** — Booking.com+FlixBus+Direct Ferries+Hoppa+eDreams
4. **Impact** — Skyscanner+Omio+Headout+World Nomads+Fever
5. **Civitatis** — tours 5-8%, instant
6. **Klook** — attractions 3-5%, instant via Impact
7. **Viator** — 300K+ tours, 8%
8. **KiwiTaxi** — transfers 30-50%

**Total revenue potential all verticals: €5,000-40,000/mo**

## SCRAPER RESULTS (2026-04-12) — COMPLETE

2,968 agencies scraped in ~10 min (30 workers):

| Metric | Count |
|--------|-------|
| Reachable sites | 1,291 (43%) |
| Sell flights | 813 (27%) |
| Have online booking | 1,160 (39%) |
| Mention API/B2B/partner | 861 (29%) |
| Have GDS integration | 70 (2.4%) |
| **API/B2B + GDS (best partners)** | **59** |
| WordPress sites | 429 |
| RSS feeds | 419 |
| WooCommerce | 174 |

**59 agencies with both API/B2B mentions AND GDS** = prime sub-agent targets (TAROM Tours, Travel Time, Air Express, Marshal Turism, Eturia, etc.)

**Output:** `/opt/ACTIVE/FLIGHTS/agentii_scraped.csv` (28 columns) + local copy

## EXISTING TOURISM DATA (already in D:\MEMORY)

| Data | Path | Records |
|------|------|---------|
| France hotels | `CLAUDE/OPT/DATA/EU_TOURISM/france_hebergements_20251220.csv` | 21,156 |
| Romania agencies (Jan) | `CLAUDE/OPT/DATA/ROMANIA/TOURISM_AGENCIES_RO_NEW.csv` | 2,405 |
| EU tourism scraper | `CLAUDE/OPT/SCRAPERS/EUROPE/TOURISM/eu_tourism_scraper.py` | Covers 7 countries |
| Tourism campaign scripts | `CLAUDE/OPT/EMAIL/campaigns/TOURISM_RO/` | send_tourism.py etc. |
| EU registries guide | `CLAUDE/OPT/DATA/EU_TOURISM/EU_TOURISM_REGISTRIES.md` | 27 countries |

## DOWNLOADABLE TOURISM DATA (not yet grabbed)

See `TOURISM_OPEN_DATA_MASTER.md` for full list. Top priorities:
- Italy INFOTRAV: 11,000 agencies (direct Excel download)
- UK ATOL: 1,616 operators (direct Excel)
- Croatia: 65,000 accommodations (CSV)
- Greece: 10,000 hotels (CSV)
- Spain regions: 38,000 combined (CSV)
- OpenStreetMap: 500,000 hotels worldwide (Overpass query)
- Wikidata: 25,000 hotels (SPARQL)

## Files Index

| File | What |
|------|------|
| `agentii_turistice_clean.csv` | All 2,968 SITUR agencies |
| `agentii_organizatoare_campaign.csv` | 1,448 Organizatoare with email (campaign CSV) |
| `flight_agencies.json` | Orchestrator campaign config |
| `templates/flight_partner_template1.txt` | Email template |
| `flights.html` | Flight search page (needs API key) |
| `price_monitor.py` | Price monitor bot (deployed to raspibig) |
| `IATA_PARTNERS_ROMANIA.md` | IATA sub-agent partner research |
| `FLIGHT_APIs_RESEARCH.md` | All API/affiliate research |
| `ULTRAPLAN_AIR_TICKETS.md` | Full implementation plan |

## Raspibig Locations

| What | Path |
|------|------|
| Campaign config | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/flight_agencies.json` |
| Template | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/template1.txt` |
| Price monitor | `/opt/ACTIVE/FLIGHTS/price_monitor.py` |
| Price monitor logs | `/opt/ACTIVE/FLIGHTS/logs/` |
| Price data | `/opt/ACTIVE/FLIGHTS/data/prices.json` |
| DB table contacts | `interjob_master.flight_agencies_campaign` |
| DB table send log | `interjob_master.flight_agencies_send_log` |
| DB table prices | `interjob_master.flight_prices` |

## Quick Start (next session)

```bash
# 1. After getting Travelpayouts API key:
ssh tudor@192.168.100.21 'echo "TEQUILA_API_KEY=your_key_here" >> /opt/ACTIVE/EMAIL/CAMPAIGNS/.env'

# 2. Deploy flights page:
python3 -c "
import ftplib
ftp = ftplib.FTP('209.124.66.6', timeout=30)
ftp.login('raspibig@loaiidil.a2hosted.com', 'Rasp1b1g2026')
try: ftp.mkd('/expatsinromania.org/flights')
except: pass
ftp.cwd('/expatsinromania.org/flights')
with open('D:/MEMORY/AIR TICKETS/flights.html','rb') as f: ftp.storbinary('STOR index.html', f)
ftp.quit()
print('DEPLOYED')
"

# 3. Add price monitor cron:
ssh tudor@192.168.100.21 'crontab -l > /tmp/cb && echo "0 */6 * * * cd /opt/ACTIVE/FLIGHTS && /opt/ACTIVE/INFRA/venv/bin/python3 price_monitor.py >> /opt/ACTIVE/FLIGHTS/logs/cron.log 2>&1" >> /tmp/cb && crontab /tmp/cb'

# 4. Launch campaign (after template approval):
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 orchestrator.py --configs configs/ --once 2>&1 | grep FLIGHT'

# 5. Check dashboard:
curl -s http://192.168.100.21:8096/flight_agencies/
```
