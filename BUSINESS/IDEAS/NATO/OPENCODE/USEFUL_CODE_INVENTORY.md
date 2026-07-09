# USEFUL CODE & PROGRAMS INVENTORY
**Comprehensive Infrastructure Reuse Analysis**
**System Scanned:** /opt/ACTIVE, /opt/ACTIVE/IDEAS, /opt/ACTIVE/INFRA
**Date:** March 21, 2026

---

## INFRASTRUCTURE OVERVIEW

**Total Systems Identified:** 200+ scripts, 50+ campaigns, 43 enrichment tools, 500K+ company records

---

## CATEGORY 1: EMAIL CAMPAIGN INFRASTRUCTURE (⭐ MOST REUSABLE FOR CAP)

### 1.1 Campaign Orchestrator
**File:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_24_7.py`

**What it does:**
- Runs 50+ email campaigns 24/7 as background processes
- Monitors campaigns, auto-restarts on failure
- Supports config-driven daily limits (50-290 emails/day)
- Telegram alerts for critical events
- PID-based process management

**Reusability for CAP:** 100%
- Add CAP_FEDERATION to campaign config
- Immediately operational (0 coding)
- Daily limit: 50 co-ops × 15 days = 750 prospects
- Cost: 1 day configuration

**Key Features to Leverage:**
```python
CAMPAIGNS = {
    "CAP_FEDERATION": {
        "enabled": True,
        "script": "CAP_FEDERATION/run_cap_federation.sh",
        "daily_limit": 50,
        "restart_delay": 300,
        "priority": True,
    }
}
```

---

### 1.2 Email Sender (Brevo Integration)
**Files:**
- `/opt/ACTIVE/EMAIL/CAMPAIGNS/.env` (credentials)
- `/opt/ACTIVE/INFRA/SKILLS/email_sender.py` (function library)

**What it does:**
- Send emails via Brevo (transactional API)
- Template-based sending
- Campaign tracking (open rates, click rates)
- Daily limit enforcement
- Error handling + retry logic

**Reusability for CAP:** 100%
- Change email template only
- Credentials already configured
- Production-proven (100K+ emails sent)

---

### 1.3 Existing Campaign Templates (50+ campaigns)
**Directory:** `/opt/ACTIVE/EMAIL/CAMPAIGNS/`

**Successful campaigns to study:**
- NECALIFICATI (90/day, unemployment outreach)
- ANOFM (90/day, job seeker outreach)
- BULGARIA_CONSTRUCTION (construction sector)
- NORWAY/sectors/ (12 Norwegian sector campaigns)

**CAP Adaptation:**
- Copy NECALIFICATI structure (most similar outreach)
- Modify email template
- Change prospect database query
- **Estimated effort:** 2 days

---

## CATEGORY 2: ENRICHMENT ENGINE (⭐ SECOND MOST REUSABLE)

### 2.1 Universal Enricher
**File:** `/opt/ACTIVE/INFRA/SKILLS/universal_enricher.py`

**What it does:**
- Enriches ANY company by CUI, name, or domain
- Checks: ONRC, telecom index, email reverse lookup, website crawl
- Fuzzy matching vs 600K+ email index
- Returns: Email, phone, address, website

**Reusability for CAP:** 90%
- Point to cap_cooperatives table
- Query Romanian co-ops (CUI-based)
- Enrich to find emails, phones
- **Estimated effort:** 1 week (adapt queries)

**Key Function:**
```python
class UniversalEnricher:
    def enrich_by_cui(self, cui: str, county: str):
        # 1. Search ONRC (Romanian company registry)
        onrc = self.search_onrc(cui)
        
        # 2. Check telecom index (600K+ emails)
        email = self.check_email_index(name, county)
        
        # 3. Website impressum crawl
        contact = self.crawl_impressum(onrc['website'])
        
        # 4. Return enriched data
        return {
            'cui': cui,
            'email': email,
            'phone': onrc['phone'] or contact['phone'],
            'address': onrc['address'],
            'website': onrc['website']
        }
```

---

### 2.2 Build Enrichment Index
**File:** `/opt/ACTIVE/INFRA/SKILLS/build_enrichment_index.py`

**What it does:**
- Builds SQLite index from ALL data sources
- Supports: ONRC, companies, contacts, telecom, external datasets
- Enables fast fuzzy searching
- Updated by cron job (daily)

**Reusability for CAP:** 100%
- Add CAP-specific sources (cooperative registries)
- Search for co-ops across 600K+ records
- **Estimated effort:** 2 hours to add new source

---

### 2.3 Fuzzy Matcher
**File:** `/opt/ACTIVE/INFRA/SKILLS/fuzzy_matcher.py`

**What it does:**
- Fuzzy string matching (Levenshtein, trigrams)
- Match company names across datasets
- Precision tuning (85%+ similarity threshold)
- PostgreSQL trigram index support

**Reusability for CAP:** 95%
- Match co-op names vs existing database
- Identify duplicates, find related entities
- **Estimated effort:** 0 (perfect fit)

**Example Use:**
```python
# Match "COOPERATIVA AGRICOLA X TARGU MURES" vs database
matches = fuzzy_matcher.search("COOPERATIVA AGRICOLA X TARGU MURES", threshold=0.85)

# Returns:
[
    {'name': 'COOPERATIVA AGRICOLA X TOPOUSENI', 'confidence': 0.92},
    {'name': 'COOPERATIVA X TARGU MURES', 'confidence': 0.88}
]
```

---

### 2.4 Auto Enricher
**File:** `/opt/ACTIVE/INFRA/SKILLS/auto_enricher.py`

**What it does:**
- Detects columns in CSV files
- Auto-enriches based on column names
- Handles: CUI, name, email, website, domain
- Batch processing (1000s of records)

**Reusability for CAP:** 85%
- Load co-op CSV from agricultural associations
- Auto-detect "Nume Cooperativă", "CUI", "Județ" columns
- Auto-enrich emails, phones
- **Estimated effort:** 3 days (test with co-op data)

---

## CATEGORY 3: DATABASE INFRASTRUCTURE

### 3.1 InterJob Master Database
**Connection:** PostgreSQL, localhost:5432, interjob_master, user: tudor

**Existing Tables:**
- `companies` (500K+ companies)
- `contacts` (200K+ records)
- `tenders` (80K procurement contracts)
- `ted_winners` (1.57M EU contract winners, 375K emails)
- `european_countries` (44 countries)

**Reusability for CAP:** 90%
- Add 2 new tables: cap_cooperatives, cap_contracts
- Reuse existing infrastructure (connection pooling, backups)
- Query ted_winners for EU tender opportunities
- **Estimated effort:** 2 days

---

### 3.2 Database Utility Scripts
**Directory:** `/opt/ACTIVE/DB/`

**Available Scripts:**
- PostgreSQL export/import
- Database backup automation
- Schema migration tools
- Performance monitoring

**Reusability for CAP:** 100%

---

## CATEGORY 4: SCRAPING FRAMEWORK

### 4.1 ConnectAmericas Scraper (MOST RELEVANT)
**File:** `/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE/scrapers/mercosur/connectamericas_scraper.py`

**What it does:**
- Scrapes 20K+ Brazilian exporters
- Search by: keyword, HS code, state
- Returns: Name, email, phone, website, products, export volume
- Features: Caching, deduplication, rate limiting

**Reusability for CAP:** 70%
- Adapt for Romanian co-op registries
- Change source URLs
- Adjust to Romanian data structure
- **Estimated effort:** 2-3 weeks

**Key Structure:**
```python
class ConnectAmericasScraper:
    SEARCH_URL = "https://connectamericas.com/api/v1/businesses"
    
    def search_by_keyword(self, keyword: str, limit: int = 100):
        # Search companies by keyword
        # Returns: List[Dict] with company data
```

---

### 4.2 Country-Specific Scrapers
**Directory:** `/opt/ACTIVE/SCRAPERS/EUROPE/`

**Available Scrapers:**
- Germany (impressum crawler, company registry)
- Nordic countries (company registries)
- Poland, Italy, France, Spain (business registries)
- Romania (ANOFM, ONRC, telecom)

**Reusability for CAP:** 90% (for international expansion)
- Month 6+: Add Bulgarian/Hungarian co-ops
- Month 12+: Add pan-European co-ops
- **Estimated effort:** 2 weeks per country

---

### 4.3 SEAP Scraper
**Directory:** `/opt/ACTIVE/IDEAS/FOOD/SUPERMARKETS_CLAUDE/CODE/`

**Available Scrapers:**
- `seap_extract.py` (contract extraction)
- `seap_cross_match.py` (contract matcher)
- `enrich_seap_winners.py` (contract winner enrichment)

**Reusability for CAP:** 95%
- Monitor SEAP food contracts (CPV 03/15)
- Match CAP co-ops to contract requirements
- Auto-alert on high-value matches
- **Estimated effort:** 3 days (filter for food/agri)

---

### 4.4 TED Scraper
**Directory:** `/opt/ACTIVE/TED/scrapers/`

**Available Scrapers:**
- `ted_scraper.py` (EU tender scraper)
- `ted_daily_monitor.py` (daily monitoring)
- `ted_api_scraper.py` (API-based scraping)

**Reusability for CAP:** 85%
- Monitor EU food tenders
- Identify Romanian/Eastern Europe opportunities
- Auto-alert on CAP-relevant tenders
- **Estimated effort:** 3 days (filter for agri)

---

## CATEGORY 5: AUTOMATION SKILLS (200+ SKILLS)

### 5.1 Enrichment Skills (43 files)
**Directory:** `/opt/ACTIVE/INFRA/SKILLS/`

**Key Skills:**
- `enrich_seap_winners.py` (SEAP contract winner enrichment)
- `eufunds_enricher.py` (EU funding enrichment)
- `onrc_enricher.py` (Romanian company registry)
- `telecom_enricher.py` (Romanian telecom records)
- `enrich_romania.py` (comprehensive Romania enrichment)

**Reusability for CAP:** 90%
- Use onrc_enricher for co-op CUI lookup
- Use telecom_enricher for email discovery
- Combine multiple enrichers for completeness
- **Estimated effort:** 1 week (integrate into CAP pipeline)

---

### 5.2 Monitoring & Alerting
**File:** `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/alerting.py`

**What it does:**
- Send Telegram alerts
- Supports: Text, HTML, code blocks
- Used throughout system (daily summaries, errors)

**Reusability for CAP:** 100%
- Daily CAP summaries
- High-value contract alerts
- Member acquisition milestones
- **Estimated effort:** 0 (perfect fit)

---

### 5.3 Outreach Automation
**Directory:** `/opt/ACTIVE/INFRA/SKILLS/`

**Available Scripts:**
- `outreach_automation.py` (automated outreach)
- `brevo_automation.py` (Brevo integration)
- `a2_whatsapp_automation.py` (WhatsApp outreach)

**Reusability for CAP:** 95%
- Automate co-op outreach sequences
- Follow-up reminders
- Response tracking
- **Estimated effort:** 1 week (customize sequences)

---

## CATEGORY 6: INFRASTRUCTURE COMPONENTS

### 6.1 Node-RED Automation
**Location:** raspibig server (192.168.100.21)

**What it does:**
- Visual workflow automation
- Integration with Telegram, email, databases
- Real-time monitoring dashboards

**Reusability for CAP:** 80%
- CAP membership workflow automation
- Real-time capacity dashboard
- Bid submission automation
- **Estimated effort:** 2 weeks (build workflows)

---

### 6.2 Shared Libraries
**Directory:** `/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/`

**Available Libraries:**
- `skills_common.py` (utility functions: sanitize, to_ascii)
- `alerting.py` (Telegram alerts)
- `email_sender.py` (email functions)
- `database.py` (PostgreSQL utilities)

**Reusability for CAP:** 100%
- All functions directly reusable
- No adaptation required
- **Estimated effort:** 0

---

## CATEGORY 7: MERCOSUR TRADE INFRASTRUCTURE (RECENT WORK)

### 7.1 Brazilian Exporters Scraper
**File:** `/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE/scrapers/mercosur/connectamericas_scraper.py`

**What it does:**
- 20K+ Brazilian exporters database
- Search by: HS code, keyword, state
- Products: Honey (0409), niobium (81), meat (02), beverages (22)
- Features: Caching, CSV export, statistics

**Reusability for CAP:** 70%
- Adapt for Romanian co-ops
- Data structure similar
- **Estimated effort:** 2-3 weeks

---

### 7.2 Apex Brasil Scraper
**File:** `/opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE/scrapers/mercosur/apex_brasil_scraper.py`

**What it does:**
- Scrapes Apex Brasil business directory
- Brazilian export companies
- Contact information extraction

**Reusability for CAP:** 60%
- Similar structure, different source
- **Estimated effort:** 3 weeks

---

## CATEGORY 8: MATCHING & ANALYSIS TOOLS

### 8.1 SEAP Food Analysis
**File:** `/opt/ACTIVE/IDEAS/NATO/OPENCODE/scripts/analyze_seap_market.py`

**What it does:**
- Analyzes 47K SEAP food contracts
- By value, CPV code, supplier
- Market size estimation

**Reusability for CAP:** 100%
- Monitor CAP-relevant contracts
- Track market trends
- **Estimated effort:** 0 (perfect fit)

---

### 8.2 Contract Winner Analysis
**Directory:** `/opt/ACTIVE/INFRA/SKILLS/contractor-enrichment/`

**Available Scripts:**
- `enrich_contractors.py` (contract winner enrichment)
- Match contractors to companies
- Identify supply chain relationships

**Reusability for CAP:** 85%
- Match subcontractors (NISARA, MATRA)
- Enrich military supplier contacts
- **Estimated effort:** 1 week

---

## INFRASTRUCTURE REUSE MATRIX

| Category | Files | Reuse for CAP | Effort | Priority |
|----------|-------|---------------|--------|----------|
| Email Campaigns | 50+ | 100% | 1 day | ⭐ HIGHEST |
| Enrichment | 43 | 90% | 1 week | ⭐ HIGHEST |
| Database | Existing | 90% | 2 days | ⭐ HIGHEST |
| Monitoring | Integrated | 100% | 0 hours | HIGH |
| Scrapers (RO) | 10+ | 90% | 3 days | HIGH |
| Scrapers (EU) | 15+ | 85% | 2 weeks | MEDIUM |
| SEAP Monitoring | 5+ | 95% | 3 days | HIGH |
| Automation | 200+ skills | 90% | 1 week | HIGH |
| Node-RED | raspibig | 80% | 2 weeks | MEDIUM |
| Mercosur Scrapers | 3 | 70% | 2-3 weeks | LOW (future) |

---

## TOTAL INFRASTRUCTURE VALUE

**Development Cost to Reproduce:**
- Email infrastructure: 20K EUR × 3 months
- Enrichment engine: 25K EUR × 3 months
- Database: 15K EUR × 2 months
- Scrapers: 30K EUR × 6 months
- Automation: 20K EUR × 4 months
- **Total to reproduce: ~110K EUR, 18 months**

**Time to Build from Scratch:** 18 months minimum
**Time to Reuse (CAP):** 6-8 weeks

**Cost savings:** ~95K EUR + 16 months

---

## PRIME CANDIDATES FOR IMMEDIATE REUSE (48 HOURS)

### 1. Campaign Orchestrator (2 hours)
```bash
# Add to /opt/ACTIVE/EMAIL/CAMPAIGNS/campaign_orchestrator_24_7.py

"CAP_FEDERATION": {
    "enabled": True,
    "script": "CAP_FEDERATION/run_cap_federation.sh",
    "daily_limit": 50,
    "restart_delay": 300,
    "priority": True,
}
```

### 2. Database Tables (4 hours)
```sql
CREATE TABLE cap_cooperatives (...);
CREATE TABLE cap_contracts (...);
```

### 3. Universal Enricher Adaptation (6 hours)
```python
# Create: /opt/ACTIVE/INFRA/SKILLS/cap_enricher.py
# Adapt: universal_enricher.py for cap_cooperatives table
```

### 4. Telegram Monitoring (2 hours)
```python
# Create: /opt/ACTIVE/INFRA/SKILLS/cap_monitor.py
# Use: existing alerting.py
```

### 5. Email Template (4 hours)
```python
# Create: /opt/ACTIVE/EMAIL/CAMPAIGNS/CAP_FEDERATION/send_cap_federation.py
# Adapt: existing campaign sender
```

**Total: 18 hours (2.5 days) to CAP operational with infrastructure**

---

## CONCLUSION

**Infrastructure Readiness:** EXCELLENT

**Key Advantages:**
1. ✅ Production-proven email campaign system
2. ✅ Comprehensive enrichment engine (600K+ index)
3. ✅ Established database with 500K+ companies
4. ✅ Real-time monitoring & alerting
5. ✅ 200+ automation skills (fully adaptable)

**Recommendation:** PROCEED with infrastructure reuse strategy
**Expected Timeline:** 6-8 weeks to first revenue
**Cost Savings:** ~95K EUR + 16 months vs. new build

**Next Step:** Review INFRASTRUCTURE_PROPOSAL.md for implementation plan
