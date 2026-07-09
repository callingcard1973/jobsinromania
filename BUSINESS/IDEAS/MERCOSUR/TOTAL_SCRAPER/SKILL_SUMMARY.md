# MERCOSUR Scraper Skills Summary

## Quick Commands

```bash
# Best approach - run enricher
cd /opt/ACTIVE/IDEAS/MERCOSUR/CLAUDE/OPENCODE/scrapers/mercosur/parallel
python3 worker_enricher.py --no-search --threads 8

# Run all workers
python3 orchestrator.py --all --sequential

# Merge results
python3 merger.py --include-existing

# Check status
python3 orchestrator.py --status
```

## Current Data

| File | Records | Location |
|------|---------|----------|
| Master JSON | 700 companies | /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final/mercosur_combined_20260322.json |
| Contacts CSV | 246 with email | /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_final/mercosur_contacts_20260322_final.csv |

## Worker Performance

| Worker | Success | Notes |
|--------|---------|-------|
| enricher | 71% | BEST - generates info@domain |
| websites | 3% | Many sites unreachable |
| associations | 0% | Needs Selenium |
| tradeshows | 0% | Needs Selenium |
| govapis | 0% | APIs not exposed |
| registries | 0% | Needs bulk download |

## Email Enrichment Strategy

```python
# Priority prefixes (in order)
prefixes = ["export", "comercial", "ventas", "sales", "info", "contact"]

# For company with website:
# 1. Extract domain
# 2. Generate emails: info@domain, contact@domain, etc.
# 3. Verify MX records exist
# 4. Return first valid
```

## Data Sources

**Working:**
- CAPECO Paraguay (grains)
- ABPA Brazil (poultry)
- Hardcoded verified exporters

**Not Working:**
- APEX Brasil API
- ProChile API
- Kompass LATAM
- UN Comtrade

## To Improve Results

1. `pip install selenium webdriver-manager` - Enable JS scraping
2. Hunter.io API key - Professional email finder
3. Manual lookup for top 50 companies
