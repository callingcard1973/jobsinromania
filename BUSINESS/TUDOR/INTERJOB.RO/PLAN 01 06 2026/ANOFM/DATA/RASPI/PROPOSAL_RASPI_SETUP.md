# RASPI ANOFM SETUP PROPOSAL

## Objective
Make raspi ANOFM pipeline work identically to raspibig with:
1. Scraper with phone normalization
2. Automated ingest to database
3. Audience rebuild for campaigns
4. Email campaign capability

## Current Status

### RASPI (192.168.100.20)
| Component | Status | Notes |
|-----------|--------|-------|
| Network | ✅ 1000 Mbps | Fixed (was 100 Mbps) |
| Scraper | ⚠️ Partial | Phone normalization NOT working |
| Database | ✅ anofm_db | 16,429 rows synced |
| Ingest | ⚠️ Needs fix | Schema mismatch |
| Audience Rebuild | ⚠️ Disabled | Ready to enable |
| Timers | ❌ All disabled | Need to activate |

### RASPIBIG (192.168.100.21)
| Component | Status | Notes |
|-----------|--------|-------|
| Network | ✅ 1000 Mbps | ✅ |
| Scraper | ✅ Updated | Phone normalization WORKING |
| Database | ✅ interjob_master | 16,429 rows |
| Ingest | ✅ Running | 3x daily |
| Audience Rebuild | ✅ Running | 3x daily |
| Campaign | ✅ Active | ANOFM_ANGAJATORI (150/day) |

## Required Changes

### 1. Fix RASPI Scraper (CRITICAL)

**Problem:** Phone normalization function exists but not being called
**Fix:** Apply raspibig scraper version with working normalization

```bash
# On raspibig
scp /opt/ACTIVE/SCRAPERS/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS/anofm_api_scraper_fixed.py tudor@192.168.100.20:/opt/ACTIVE/INTERJOB/anofm_scraper.py

# Or copy via local machine
# Download from raspibig → upload to raspi
```

**Expected output:**
- Phone format: `+40786793500` (not `0786793500`)
- Format: `+40241505174` (not `0241/505174`)

### 2. Fix RASPI Ingest

**Problem:** Ingest script expects interjob_master schema, raspi has anofm_db
**Options:**

**Option A - Use raspibig ingest:**
1. Run scrape on raspi → CSV
2. Run ingest on raspibig → interjob_master
3. Sync interjob_master → anofm_db on raspi

**Option B - Modify raspi ingest:**
1. Update `/opt/ACTIVE/INTERJOB/ingest/ingest_anofm.py`
2. Connect to `anofm_db` instead of `interjob_master`
3. Test upsert logic

**Recommended:** Option A (simpler, proven)

### 3. Enable RASPI Timers

```bash
# On raspibig - get timer files
cat /etc/systemd/system/anofm-scraper.timer
cat /etc/systemd/system/anofm-ingest.timer
cat /etc/systemd/system/anofm-audience-rebuild.timer

# Copy to rasppi and enable
sudo systemctl enable anofm-scraper.timer
sudo systemctl enable anofm-ingest.timer
sudo systemctl enable anofm-audience-rebuild.timer
```

**Schedule:**
- Scraper: Mon-Fri 08:25, 12:25, 15:59
- Ingest: Mon-Fri 09:00, 13:00, 16:30
- Audience Rebuild: Mon-Fri 09:10, 13:10, 16:40

### 4. Setup RASPI Campaign

**Copy from raspibig:**
```bash
# Campaign script
scp -r /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/ tudor@192.168.100.20:/opt/ACTIVE/EMAIL/CAMPAIGNS/

# Environment variables
cat ~/.env on raspibig → create on raspi
```

**Update raspi campaign script:**
```python
# Change DB connection
conn = psycopg2.connect(
    host="localhost",
    database="anofm_db",
    user="tudor",
    password="tudor"
)
```

**Test:**
```bash
python3 campaign_anofm_angajatori.py --dry-run --limit 5
```

### 5. Sync Database

**Option A - One-time full sync:**
```bash
# On raspibig
pg_dump -h localhost -U tudor interjob_master -t ij_jobs | \
  ssh tudor@192.168.100.20 "psql -U tudor anofm_db"
```

**Option B - Ongoing auto-sync:**
```bash
# Add to raspibig crontab
# Every 30 min: sync new records to raspi
```

## Data Flow (Target State)

```
ANOFM API
    ↓
raspi: anofm_scraper.py (4 workers)
    ↓
CSV (8,365 jobs, normalized phones)
    ↓
raspi: anofm_db.ij_jobs
    ↓
raspi: anofm_angajatori_rebuild.py
    ↓
Deduped CSV (1 company, 1 job)
    ↓
raspi: campaign_anofm_angajatori.py
    ↓
150 emails/day via Brevo
```

## Parallel Scraping Config

**Already working on raspi:**
```bash
# 4 parallel workers
# Pages: 1-21, 22-42, 43-63, 64-84
# Time: ~2.5 min (vs ~9.5 min serial)
```

**Add to raspibig:**
```bash
# Update scraper on raspibig too
# Benefits: 4x speed improvement
```

## Implementation Plan

### Phase 1 - Scraper Fix (Day 1)
- [ ] Copy raspibig scraper to raspi
- [ ] Test normalization: `python3 anofm_scraper.py --test --csv`
- [ ] Verify phone format: `+40XXXXXXX`
- [ ] Update raspibig scraper with parallel mode

### Phase 2 - Database & Ingest (Day 2)
- [ ] Option A: Use raspibig for ingest
- [ ] Sync interjob_master → anofm_db
- [ ] Test data in anofm_db

### Phase 3 - Timers & Automation (Day 3)
- [ ] Copy timer files from raspibig
- [ ] Enable timers on raspi
- [ ] Test first automated run
- [ ] Monitor logs

### Phase 4 - Campaign Setup (Day 4)
- [ ] Copy ANOFM_ANGAJATORI to raspi
- [ ] Update DB connection to anofm_db
- [ ] Test dry-run: 5 emails
- [ ] Test live: 10 emails
- [ ] Monitor first 24h

### Phase 5 - Production (Day 5)
- [ ] Full 150/day cap
- [ ] Monitor 1 week
- [ ] Compare results raspibig vs raspi

## Comparison: RASPI vs RASPIBIG

| Feature | RASPI | RASPIBIG | Target |
|---------|-------|----------|--------|
| Network | 1000 Mbps ✅ | 1000 Mbps ✅ | Both 1000 |
| Scraper | ⚠️ Partial | ✅ Working | ✅ |
| Phone Norm | ❌ Broken | ✅ Working | ✅ |
| Parallel | ✅ 4 workers | ❌ Serial | ✅ Both |
| DB | anofm_db (synced) | interjob_master | Both synced |
| Ingest | ⚠️ Needs fix | ✅ Working | ✅ |
| Campaign | ⏸️ Paused | ✅ Active | ✅ Both |
| Timers | ❌ Disabled | ✅ Enabled | ✅ |

## Rollout Strategy

### Option 1 - Parallel Running (Recommended)
- Both machines run independently
- Redundancy: if one fails, other continues
- Can split workload: raspibig (primaries) + raspi (backup)

### Option 2 - Hot Standby
- raspibig runs primary
- raspi runs in standby
- Failover: switch DNS/orchestrator

### Option 3 - Split Workload
- raspibig: Mon/Wed/Fri
- raspi: Tue/Thu
- Both: Weekends (if needed)

**Recommended:** Option 1 (parallel running)

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scraper breaks | High | Keep backups, test thoroughly |
| Ingest fails | High | Manual fallback, raspibig backup |
| Campaign dupes | Medium | Dedup by job_id, sync sent.csv |
| Network fails | Low | Local cache, retry logic |
| Disk full | Low | Monitor, cleanup old CSVs |

## Success Criteria

1. ✅ Scraper produces normalized phones (`+40...`)
2. ✅ Database updated automatically (3x daily)
3. ✅ Audience rebuilt (3x daily)
4. ✅ Campaign sends 150 emails/day
5. ✅ Zero duplicate emails
6. ✅ Logs show no errors
7. ✅ Performance: scrape < 3 min (parallel)

## Monitoring

### Daily Checks
```bash
# On raspi
systemctl status anofm-*.timer
tail -50 /var/log/syslog | grep anofm
wc -l /opt/ACTIVE/ANOFM_DATA/csv/latest.csv
ps aux | grep anofm_scraper
```

### Alerts
- Scraper fails (no CSV output)
- Ingest errors (check logs)
- Campaign not sending (check sent.csv)
- Disk space < 20%
- API rate limits (check logs)

---

**Created:** 2026-06-21
**Status:** Proposal ready for review
**Next:** Phase 1 - Fix scraper