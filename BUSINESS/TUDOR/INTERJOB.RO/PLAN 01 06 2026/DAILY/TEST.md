# End-to-End Test Guide

## Prerequisites

```bash
# On raspibig:
pip install psycopg2-binary requests deep-translator

# Verify DB connectivity
psql -h localhost -U tudor -d interjob_master -c "SELECT count(*) FROM ij_jobs LIMIT 1;"
```

## Test 1: Dry-Run (Validate + Generate, No Publish)

```bash
cd /opt/ACTIVE/EVENT_PUBLISHER

# Run with --dry-run flag
python3 orchestrator.py --dry-run

# Expected output:
# ✅ ORCHESTRATION COMPLETE
# _workspace/01_validator_output.json (validation results)
# _workspace/02_content_output.json (generated articles)
# _workspace/final_report.json (summary)
```

**Verify outputs:**
```bash
cat _workspace/01_validator_output.json | jq '.status'  # Should be "valid"
cat _workspace/02_content_output.json | jq '.articles.ro.title'  # RO article title
cat _workspace/02_content_output.json | jq '.articles.en.title'  # EN article title
```

## Test 2: Full Run (All Phases Including Publishing)

```bash
# WARNING: This will PUBLISH articles to interjob.ro
python3 orchestrator.py

# Expected output:
# ✅ ORCHESTRATION COMPLETE
# _workspace/03_publisher_output.json (post IDs)
# _workspace/04_monitor_output.json (performance metrics)

# Verify posts published
curl -s https://interjob.ro/piata-muncii-2026-06-23/ | head -20
curl -s https://interjob.ro/job-market-2026-06-23/ | head -20
```

## Test 3: Individual Agent Testing

```bash
# Test data-validator alone
cat > test_validator.json << EOF
{
  "db_host": "localhost",
  "db_port": 5432,
  "db_name": "interjob_master",
  "db_user": "tudor",
  "db_pass": "$(grep '^localhost' ~/.pgpass | cut -d: -f5)",
  "eures_base": "/opt/ACTIVE/SCRAPER_DATA/csv/EURES",
  "eures_countries": ["Norway", "Denmark", "Sweden", "Finland", "Germany", "Netherlands", "France"],
  "dry_run": false
}
EOF

python3 agent_data_validator.py < test_validator.json | jq '.status'
```

## Logs & Monitoring

```bash
# Watch orchestrator log
tail -f /opt/ACTIVE/INFRA/LOGS/daily_roundup.log

# Check workspace
ls -la _workspace/
cat _workspace/final_report.json
```

## Success Criteria

- [ ] Dry-run completes with 4 JSON output files
- [ ] `validator_output.status` = "valid"
- [ ] `content_output.articles.ro` and `.en` both present and > 5000 chars
- [ ] Full run publishes posts (post_ids > 0)
- [ ] Monitor reports TTFB < 2000ms
- [ ] Final report saved to `_workspace/final_report.json`
