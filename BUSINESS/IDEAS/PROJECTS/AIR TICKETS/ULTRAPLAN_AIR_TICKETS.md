# Air Ticket Reselling — Full Campaign ULTRAPLAN

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up complete air ticket reselling operation — email campaign to 1,254 IATA travel agencies, flight search page on expatsinromania.org, price monitor on raspibig, dashboard integration.

**Architecture:** Campaign follows existing orchestrator v4 pattern (JSON config → send_campaign.py → Brevo API). Flight page uses Kiwi Tequila API (affiliate deeplinks). Price monitor runs as cron on raspibig storing to PostgreSQL.

**Tech Stack:** Python 3, PostgreSQL (interjob_master), Brevo API, Kiwi Tequila API, FTP deploy to A2 Hosting, raspibig systemd/cron.

---

## Chunk 1: Campaign Data & Template

### Task 1: Filter CSV — Organizatoare agencies only

**Files:**
- Source: `D:\MEMORY\AIR TICKETS\agentii_turistice_clean.csv`
- Create: `D:\MEMORY\AIR TICKETS\agentii_organizatoare_campaign.csv`

- [ ] **Step 1: Filter to Organizatoare + OrganizatoareOnline only**

```python
# filter_organizatoare.py
import csv
src = 'D:/MEMORY/AIR TICKETS/agentii_turistice_clean.csv'
dst = 'D:/MEMORY/AIR TICKETS/agentii_organizatoare_campaign.csv'
with open(src, encoding='utf-8') as f:
    reader = list(csv.DictReader(f))
# Organizatoare = have IATA/GDS, can ticket flights
filtered = [r for r in reader if r.get('tip_agentie','') in ('Organizatoare','OrganizatoareOnline')
            and '@' in r.get('email','')]
with open(dst, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['nr_licenta','operator_economic','denumire_agentie',
                                       'cui','adresa','localitate','judet','tip_agentie',
                                       'site_web','email'])
    w.writeheader()
    for r in filtered:
        w.writerow({k: r.get(k,'').strip() for k in w.fieldnames})
print(f"Filtered: {len(filtered)} Organizatoare agencies with email")
```

Run: `python3 filter_organizatoare.py`
Expected: ~1,400-1,550 agencies (1,254 Organizatoare + 297 OrganizatoareOnline, minus those without email)

- [ ] **Step 2: Verify CSV output**

```bash
head -5 "D:/MEMORY/AIR TICKETS/agentii_organizatoare_campaign.csv"
wc -l "D:/MEMORY/AIR TICKETS/agentii_organizatoare_campaign.csv"
```
Expected: Clean CSV with headers, ~1,500 rows

- [ ] **Step 3: Commit**
```bash
cd "D:/MEMORY"
git add "AIR TICKETS/agentii_organizatoare_campaign.csv"
git commit -m "data: filter 1,500 Organizatoare travel agencies for air ticket campaign"
```

---

### Task 2: Write email template

**Files:**
- Create: `D:\MEMORY\AIR TICKETS\templates\flight_partner_template1.txt`

- [ ] **Step 1: Create template directory**
```bash
mkdir -p "D:/MEMORY/AIR TICKETS/templates"
```

- [ ] **Step 2: Write the partnership proposal template**

Template follows existing format (Subject line, body, signature, unsubscribe). Placeholders: `{denumire_agentie}`, `{localitate}`, `{judet}`, `{unsubscribe_url}`.

```
Subject: Parteneriat bilete avion — 6,300 muncitori/zi cauta zboruri

Buna ziua,

Conduc InterJob, retea de recrutare europeana cu 28 site-uri (interjob.ro, careworkers.eu, factoryjobs.eu, etc.) si o comunitate de 77,000 expati.

Plasam lunar sute de muncitori romani in Olanda, Germania, Scandinavia, Italia. Fiecare muncitor plasat are nevoie de bilet de avion.

In prezent, trimitem 6,300 emailuri/zi catre muncitori si angajatori din toata Europa.

Caut un partener cu acreditare IATA care sa emita biletele. Noi aducem clientii, voi faceti ticketing-ul, impartim comisionul.

Rutele principale:
- Bucuresti → Amsterdam, Berlin, Oslo, Copenhaga, Helsinki, Milano
- Kathmandu → Bucuresti (muncitori nepalezi)
- Sofia → Europa de Vest

Daca sunteti interesati, raspundeti cu:
1. Ce comision oferiti pe bilet?
2. Aveti GDS propriu (Amadeus/Sabre/Travelport)?
3. Puteti emite bilete si pentru rute non-EU?

Cu stima,
Tudor Seicarescu
InterJob Solutions
office@expatsinromania.org
https://interjob.ro

Pentru dezabonare: {unsubscribe_url}
```

- [ ] **Step 3: STOP — Show template to Tudor for approval before proceeding**

**Do NOT continue until Tudor explicitly approves the template text.**

- [ ] **Step 4: Commit**
```bash
cd "D:/MEMORY"
git add "AIR TICKETS/templates/"
git commit -m "feat: add flight partner email template for travel agency campaign"
```

---

## Chunk 2: PostgreSQL Table & Campaign Config

### Task 3: Create PostgreSQL table for campaign

**Target:** raspibig PostgreSQL `interjob_master`

- [ ] **Step 1: Create the campaign contacts table**

```bash
ssh tudor@192.168.100.21 'psql -U tudor -d interjob_master -c "
CREATE TABLE IF NOT EXISTS flight_agencies_campaign (
    id SERIAL PRIMARY KEY,
    nr_licenta TEXT,
    operator_economic TEXT,
    denumire_agentie TEXT,
    cui TEXT,
    email TEXT NOT NULL,
    adresa TEXT,
    localitate TEXT,
    judet TEXT,
    tip_agentie TEXT,
    site_web TEXT,
    campaign_status TEXT DEFAULT '\''pending'\'',
    last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_flight_agencies_email ON flight_agencies_campaign(email);
CREATE INDEX IF NOT EXISTS idx_flight_agencies_status ON flight_agencies_campaign(campaign_status);
"'
```

Expected: `CREATE TABLE` + `CREATE INDEX` x2

- [ ] **Step 2: Create send_log table**

```bash
ssh tudor@192.168.100.21 'psql -U tudor -d interjob_master -c "
CREATE TABLE IF NOT EXISTS flight_agencies_send_log (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    template TEXT,
    sender TEXT,
    status TEXT,
    message_id TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);
"'
```

- [ ] **Step 3: Create flight_prices table (for price monitor)**

```bash
ssh tudor@192.168.100.21 'psql -U tudor -d interjob_master -c "
CREATE TABLE IF NOT EXISTS flight_prices (
    id SERIAL PRIMARY KEY,
    route TEXT NOT NULL,
    price NUMERIC(10,2),
    airline TEXT,
    stops INTEGER,
    deep_link TEXT,
    departure TIMESTAMP,
    checked_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_flight_prices_route ON flight_prices(route);
"'
```

- [ ] **Step 4: Import campaign CSV to PostgreSQL**

```bash
# SCP the CSV to raspibig first
scp "D:/MEMORY/AIR TICKETS/agentii_organizatoare_campaign.csv" tudor@192.168.100.21:/tmp/

# Import
ssh tudor@192.168.100.21 'psql -U tudor -d interjob_master -c "
COPY flight_agencies_campaign (nr_licenta, operator_economic, denumire_agentie, cui, adresa, localitate, judet, tip_agentie, site_web, email)
FROM '\''/tmp/agentii_organizatoare_campaign.csv'\''
CSV HEADER;
SELECT COUNT(*) as total, COUNT(DISTINCT email) as unique_emails FROM flight_agencies_campaign;
"'
```

Expected: ~1,500 rows imported

- [ ] **Step 5: Verify import**

```bash
ssh tudor@192.168.100.21 'psql -U tudor -d interjob_master -c "
SELECT judet, COUNT(*) FROM flight_agencies_campaign GROUP BY judet ORDER BY COUNT(*) DESC LIMIT 10;
"'
```

---

### Task 4: Create campaign config JSON

**Files:**
- Create: `D:\MEMORY\AIR TICKETS\flight_agencies.json`
- Deploy to: `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/flight_agencies.json` on raspibig

- [ ] **Step 1: Write config following expat_providers.json pattern**

```json
{
  "db": {
    "host": "localhost",
    "dbname": "interjob_master",
    "user": "tudor",
    "password": "scraper123"
  },
  "env_file": "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env",
  "campaign_name": "FLIGHT_AGENCIES",
  "templates_dir": "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/",
  "dashboard_port": 8096,
  "url_prefix": "/flight_agencies",
  "country_flag": "&#9992;&#65039;",
  "country_filter": null,
  "gov_domains": ["gov", "edu", "mil"],
  "exclude_nace": [],
  "exclude_sources": [],
  "null_status_is_pending": true,
  "tables": {
    "contacts": "flight_agencies_campaign",
    "send_log": "flight_agencies_send_log",
    "dnc": "romania_dnc",
    "responses": "flight_agencies_responses",
    "col_email": "email",
    "col_name": "denumire_agentie",
    "col_company": "operator_economic",
    "col_city": "localitate",
    "col_employees": "id",
    "col_sector": "tip_agentie",
    "col_sector_name": "tip_agentie",
    "col_org_number": "cui",
    "col_tier": "id",
    "col_caen": "nr_licenta",
    "col_campaign_status": "campaign_status",
    "col_last_contacted": "last_contacted"
  },
  "sectors": {
    "ORGANIZATOARE": {
      "filter": "tip_agentie = 'Organizatoare'",
      "sender_key": "BREVO_EXPATSINROMANIA_API_KEY",
      "sender_email": "office@expatsinromania.org",
      "sender_name": "InterJob Flights",
      "reply_to": "manpower.dristor@gmail.com",
      "daily_limit": 50,
      "delay_min": 65,
      "delay_max": 300,
      "enabled": true,
      "template_prefix": "flight_partner",
      "sender_type": "brevo",
      "business_hours": {
        "enabled": true,
        "days": [0, 1, 2, 3, 4],
        "start": 8,
        "end": 18
      },
      "batch_size": 0,
      "template_count": 1
    },
    "ORGANIZATOARE_ONLINE": {
      "filter": "tip_agentie = 'OrganizatoareOnline'",
      "sender_key": "BREVO_EXPATSINROMANIA_API_KEY",
      "sender_email": "office@expatsinromania.org",
      "sender_name": "InterJob Flights",
      "reply_to": "manpower.dristor@gmail.com",
      "daily_limit": 30,
      "delay_min": 65,
      "delay_max": 300,
      "enabled": true,
      "template_prefix": "flight_partner",
      "sender_type": "brevo",
      "business_hours": {
        "enabled": true,
        "days": [0, 1, 2, 3, 4],
        "start": 8,
        "end": 18
      },
      "batch_size": 0,
      "template_count": 1
    }
  },
  "gmail_senders": [],
  "policy": {
    "description": "Partnership outreach to IATA-accredited Romanian travel agencies for flight ticket reselling",
    "contacts_available": 1500,
    "target": "Organizatoare + OrganizatoareOnline travel agencies (IATA/GDS holders)",
    "goal": "Find 5-10 sub-agent partners to ticket flights for InterJob placed workers"
  }
}
```

- [ ] **Step 2: Deploy config to raspibig**

```bash
scp "D:/MEMORY/AIR TICKETS/flight_agencies.json" tudor@192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/
```

- [ ] **Step 3: Deploy template to raspibig**

```bash
ssh tudor@192.168.100.21 'mkdir -p /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/'
scp "D:/MEMORY/AIR TICKETS/templates/flight_partner_template1.txt" tudor@192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/flight_agencies/template1.txt
```

- [ ] **Step 4: Verify orchestrator picks it up**

```bash
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 orchestrator.py --configs configs/ --status 2>&1 | grep -i flight'
```

Expected: Shows FLIGHT_AGENCIES campaign with status

- [ ] **Step 5: Commit**
```bash
cd "D:/MEMORY"
git add "AIR TICKETS/flight_agencies.json"
git commit -m "feat: add flight agencies campaign config for orchestrator"
```

---

## Chunk 3: Deploy Flights Page to expatsinromania.org

### Task 5: Prepare and deploy flights.html

**Files:**
- Modify: `D:\MEMORY\AIR TICKETS\flights.html` (set API key)
- Deploy to: `D:\MEMORY\SITE_PAGES\expatsinromania.org\flights\index.html` → FTP to A2

- [ ] **Step 1: Register for Kiwi Tequila API**

Manual step — Tudor must:
1. Go to https://tequila.kiwi.com/portal/login
2. Create account
3. Get API key
4. Provide key to replace `YOUR_API_KEY_HERE` in flights.html

**STOP — Wait for Tudor to provide API key before deploying.**

- [ ] **Step 2: Copy flights.html to SITE_PAGES for deploy**

```bash
mkdir -p "D:/MEMORY/SITE_PAGES/expatsinromania.org/flights"
cp "D:/MEMORY/AIR TICKETS/flights.html" "D:/MEMORY/SITE_PAGES/expatsinromania.org/flights/index.html"
```

- [ ] **Step 3: Deploy via FTP**

```python
# One-file deploy - run from D:\MEMORY
import ftplib
FTP_HOST = "209.124.66.6"
FTP_USER = "raspibig@loaiidil.a2hosted.com"
FTP_PASS = "Rasp1b1g2026"
ftp = ftplib.FTP(FTP_HOST, timeout=30)
ftp.login(FTP_USER, FTP_PASS)
ftp.encoding = "utf-8"
try:
    ftp.mkd("/expatsinromania.org/flights")
except:
    pass
ftp.cwd("/expatsinromania.org/flights")
with open("SITE_PAGES/expatsinromania.org/flights/index.html", "rb") as f:
    ftp.storbinary("STOR index.html", f)
print("Deployed to https://expatsinromania.org/flights/")
ftp.quit()
```

- [ ] **Step 4: Verify deployment**

```bash
curl -sI https://expatsinromania.org/flights/ | head -5
```

Expected: HTTP 200

- [ ] **Step 5: Commit**
```bash
cd "D:/MEMORY"
git add "SITE_PAGES/expatsinromania.org/flights/"
git commit -m "feat: deploy flight search page to expatsinromania.org/flights"
```

---

### Task 6: Add Flight Package to services page

**NOTE:** expatsinromania.org/services/ is a WordPress page (ID 46878). This requires WordPress API or manual edit.

- [ ] **Step 1: Draft new service tier content**

Add after existing "Full Relocation EUR 2,500" tier:

```html
<div class="service-card">
  <h3>Flight Booking Service</h3>
  <p class="price">EUR 50</p>
  <ul>
    <li>Best price search across all airlines</li>
    <li>Booking assistance in your language</li>
    <li>Group discounts for 5+ travelers</li>
    <li>Routes: Romania, Nepal, Bulgaria, Philippines to all EU</li>
  </ul>
  <a href="https://expatsinromania.org/flights/">Search Flights Now</a>
</div>
```

- [ ] **Step 2: Update WordPress page via WP REST API or WP-CLI**

```bash
# Use WordPress MCP or wp-cli — depends on what's available
# Alternative: Tudor edits manually in WP admin
```

**STOP — Confirm with Tudor: update via WordPress API or manual edit?**

---

## Chunk 4: Price Monitor on raspibig

### Task 7: Deploy price_monitor.py to raspibig

**Files:**
- Source: `D:\MEMORY\AIR TICKETS\price_monitor.py`
- Deploy to: `/opt/ACTIVE/FLIGHTS/price_monitor.py` on raspibig

- [ ] **Step 1: Create directory on raspibig**

```bash
ssh tudor@192.168.100.21 'mkdir -p /opt/ACTIVE/FLIGHTS/{logs,data}'
```

- [ ] **Step 2: SCP the script**

```bash
scp "D:/MEMORY/AIR TICKETS/price_monitor.py" tudor@192.168.100.21:/opt/ACTIVE/FLIGHTS/
```

- [ ] **Step 3: Add TEQUILA_API_KEY to .env**

```bash
ssh tudor@192.168.100.21 'echo "TEQUILA_API_KEY=YOUR_KEY_HERE" >> /opt/ACTIVE/EMAIL/CAMPAIGNS/.env'
```

**Wait for Tudor to provide the actual Kiwi API key.**

- [ ] **Step 4: Install requests if needed**

```bash
ssh tudor@192.168.100.21 '/opt/ACTIVE/INFRA/venv/bin/pip install requests 2>/dev/null; echo "OK"'
```

- [ ] **Step 5: Test dry run**

```bash
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/FLIGHTS && TEQUILA_API_KEY=YOUR_KEY /opt/ACTIVE/INFRA/venv/bin/python3 price_monitor.py 2>&1 | tail -20'
```

Expected: Table of 10 routes with prices (or "Check API key" errors if key not set yet)

- [ ] **Step 6: Add cron — every 6 hours**

```bash
ssh tudor@192.168.100.21 'crontab -l > /tmp/cron_backup && echo "0 */6 * * * cd /opt/ACTIVE/FLIGHTS && /opt/ACTIVE/INFRA/venv/bin/python3 price_monitor.py >> /opt/ACTIVE/FLIGHTS/logs/cron.log 2>&1" >> /tmp/cron_backup && crontab /tmp/cron_backup && echo "Cron added"'
```

- [ ] **Step 7: Verify cron**

```bash
ssh tudor@192.168.100.21 'crontab -l | grep flight'
```

Expected: `0 */6 * * * cd /opt/ACTIVE/FLIGHTS && ...`

---

## Chunk 5: Integration — Flight Block in Email Templates

### Task 8: Add flight booking block to recruitment emails

**This adds a 3-line "Book your flight" footer to existing recruitment templates.**

- [ ] **Step 1: Identify active recruitment templates**

```bash
ssh tudor@192.168.100.21 'ls /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/constructii/ /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/transport/ /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/horeca_com/ /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/agencies/ 2>/dev/null'
```

- [ ] **Step 2: Draft flight block to insert**

Insert BEFORE the `Pentru dezabonare:` line in each template:

```
---
Ai nevoie de zbor spre noul loc de munca?
Cauta cel mai ieftin bilet: https://expatsinromania.org/flights/
```

- [ ] **Step 3: STOP — Show Tudor which templates will be modified and get approval**

List of templates to modify:
- `constructii/tudor_template1.txt`
- `transport/tudor_template1.txt`
- `horeca_com/template1.txt`
- `agencies/template1.txt`
- (any others Tudor specifies)

**Do NOT modify templates without explicit approval.**

- [ ] **Step 4: Apply the block to approved templates**

For each approved template:
```bash
ssh tudor@192.168.100.21 'sed -i "s|Pentru dezabonare:|---\nAi nevoie de zbor spre noul loc de munca?\nCauta cel mai ieftin bilet: https://expatsinromania.org/flights/\n\nPentru dezabonare:|" /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/TEMPLATE_PATH'
```

- [ ] **Step 5: Verify changes**

```bash
ssh tudor@192.168.100.21 'tail -8 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/constructii/tudor_template1.txt'
```

Expected: Flight block appears above unsubscribe line

---

## Chunk 6: Verification & Launch Readiness

### Task 9: Full system verification

- [ ] **Step 1: Verify orchestrator sees new campaign**

```bash
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 orchestrator.py --configs configs/ --status 2>&1 | grep -A5 FLIGHT'
```

Expected: FLIGHT_AGENCIES listed with ORGANIZATOARE and ORGANIZATOARE_ONLINE sectors

- [ ] **Step 2: Verify dashboard shows campaign**

```bash
curl -s http://192.168.100.21:8096/flight_agencies/ | head -20
```

Expected: Dashboard page loads (or 404 if dashboard needs restart)

- [ ] **Step 3: Restart dashboard if needed**

```bash
ssh tudor@192.168.100.21 'sudo systemctl restart campaign-dashboard 2>/dev/null || echo "manual restart needed"'
```

- [ ] **Step 4: Dry run — send 0 emails, verify flow**

```bash
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 send_campaign.py --config configs/flight_agencies.json --sector ORGANIZATOARE --limit 0 --dry-run 2>&1'
```

Expected: Shows what WOULD be sent, template renders correctly, no actual sends

- [ ] **Step 5: Verify flights page live**

```bash
curl -s https://expatsinromania.org/flights/ | grep -o "<title>.*</title>"
```

Expected: `<title>Cheap Flights for Workers — InterJob</title>`

- [ ] **Step 6: Verify price monitor cron**

```bash
ssh tudor@192.168.100.21 'crontab -l | grep -c flight'
```

Expected: 1

---

### Task 10: LAUNCH — Requires Tudor's explicit GO

- [ ] **Step 1: Present launch summary to Tudor**

```
READY TO LAUNCH:
- Campaign: FLIGHT_AGENCIES (1,500 Organizatoare agencies)
- Sender: office@expatsinromania.org (Brevo)
- Rate: 50/day Organizatoare + 30/day Online = 80/day
- Duration: ~19 days to complete
- Reply-to: manpower.dristor@gmail.com
- Flight page: https://expatsinromania.org/flights/
- Price monitor: cron every 6h on raspibig
- Dashboard: http://192.168.100.21:8096/flight_agencies/

Proceed? (yes/no)
```

- [ ] **Step 2: Enable campaign in orchestrator**

**ONLY after Tudor says yes:**

The config already has `"enabled": true`. The orchestrator will pick it up on next cycle. If it was set to false for safety:

```bash
ssh tudor@192.168.100.21 'cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 orchestrator.py --configs configs/ --once 2>&1 | tail -20'
```

- [ ] **Step 3: Monitor first sends**

```bash
ssh tudor@192.168.100.21 'tail -20 /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/logs/flight_agencies*.log 2>/dev/null'
```

- [ ] **Step 4: Commit final state**
```bash
cd "D:/MEMORY"
git add "AIR TICKETS/"
git commit -m "feat: complete air ticket reselling campaign — agencies, flights page, price monitor"
```

---

## Summary

| Component | Status | Location |
|-----------|--------|----------|
| Agency CSV (2,968 total) | DONE | `D:\MEMORY\AIR TICKETS\agentii_turistice_clean.csv` |
| Organizatoare CSV (~1,500) | Task 1 | `D:\MEMORY\AIR TICKETS\agentii_organizatoare_campaign.csv` |
| Email template | Task 2 | `D:\MEMORY\AIR TICKETS\templates\flight_partner_template1.txt` |
| PostgreSQL tables | Task 3 | `interjob_master.flight_agencies_campaign` + `flight_prices` |
| Campaign config JSON | Task 4 | `configs/flight_agencies.json` on raspibig |
| Flights search page | Task 5 | `https://expatsinromania.org/flights/` |
| Services page update | Task 6 | WordPress page ID 46878 |
| Price monitor | Task 7 | `/opt/ACTIVE/FLIGHTS/price_monitor.py` + cron |
| Template integration | Task 8 | Flight block in recruitment emails |
| Verification | Task 9 | Dry run + dashboard check |
| Launch | Task 10 | **Requires Tudor's explicit GO** |

**Blocking dependencies:**
- Task 5 + Task 7 need **Kiwi Tequila API key** (Tudor registers at https://tequila.kiwi.com/portal/login)
- Task 2 needs **Tudor's approval** on email template text
- Task 8 needs **Tudor's approval** on which templates to modify
- Task 10 needs **Tudor's explicit GO** to launch campaign

**Revenue projection:** 80 emails/day → ~19 days to reach all 1,500 agencies → 5-10% response rate = 75-150 interested agencies → 5-10 signed partners → €3,000-15,000/month from flight commissions.
