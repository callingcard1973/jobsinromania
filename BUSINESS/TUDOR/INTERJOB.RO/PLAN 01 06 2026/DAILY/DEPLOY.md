# Deployment Checklist

## Step 1: Verify Raspibig Prerequisites ✅

On raspibig (192.168.100.21):

```bash
# Python 3 + packages
python3 --version  # Should be 3.9+
pip install psycopg2-binary requests deep-translator

# Database connectivity
psql -h localhost -U tudor -d interjob_master -c "SELECT 1;"

# Directories exist
mkdir -p /opt/ACTIVE/EVENT_PUBLISHER
mkdir -p /opt/ACTIVE/INFRA/LOGS
```

## Step 2: Deploy Files (Laptop)

Copy files to raspibig:

```bash
# From D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\DAILY\

scp orchestrator.py tudor@192.168.100.21:/opt/ACTIVE/EVENT_PUBLISHER/
scp agent_*.py tudor@192.168.100.21:/opt/ACTIVE/EVENT_PUBLISHER/
scp -r .claude tudor@192.168.100.21:/opt/ACTIVE/EVENT_PUBLISHER/
scp TEST.md tudor@192.168.100.21:/opt/ACTIVE/EVENT_PUBLISHER/
scp setup_cron.sh tudor@192.168.100.21:/opt/ACTIVE/EVENT_PUBLISHER/

# Make executable
ssh tudor@192.168.100.21 'chmod +x /opt/ACTIVE/EVENT_PUBLISHER/*.py /opt/ACTIVE/EVENT_PUBLISHER/*.sh'
```

## Step 3: Test Dry-Run

On raspibig:

```bash
cd /opt/ACTIVE/EVENT_PUBLISHER
python3 orchestrator.py --dry-run

# Expected: ✅ ORCHESTRATION COMPLETE
#           _workspace/01_validator_output.json
#           _workspace/02_content_output.json
#           _workspace/final_report.json
```

Verify validator passed:
```bash
cat _workspace/01_validator_output.json | jq '.status'  # "valid"
cat _workspace/01_validator_output.json | jq '.anofm_total'  # Should be > 2000
```

## Step 4: Setup Cron

On raspibig:

```bash
cd /opt/ACTIVE/EVENT_PUBLISHER
bash setup_cron.sh

# Verify
crontab -l | grep orchestrator
```

Expected output:
```
0 9 * * * cd /opt/ACTIVE/EVENT_PUBLISHER && python3 orchestrator.py >> /opt/ACTIVE/INFRA/LOGS/daily_roundup.log 2>&1
```

## Step 5: Monitor First Run

At 09:00 UTC tomorrow (or run manually):

```bash
# Watch log as it runs
tail -f /opt/ACTIVE/INFRA/LOGS/daily_roundup.log

# After run completes
cat _workspace/final_report.json | jq '.'
```

## Rollback Plan

If something fails:

```bash
# Remove cron entry
crontab -e  # Delete the daily_roundup line

# Restore original daily_roundup.py (if needed)
cp daily_roundup_20260603_old.py daily_roundup.py

# Inspect failed run
cat _workspace_prev_*/final_report.json
```

## Success Indicators

- [ ] Dry-run produces 3 JSON files (validator, content, final_report)
- [ ] validator.status = "valid"
- [ ] content.articles.ro.content_html > 5000 chars
- [ ] content.articles.en.content_html > 5000 chars
- [ ] Cron entry visible in `crontab -l`
- [ ] First production run (09:00 UTC) completes with post_ids in publisher output
- [ ] Posts appear on https://interjob.ro (check `/piata-muncii-YYYY-MM-DD/` and `/job-market-YYYY-MM-DD/`)

## Troubleshooting

| Issue | Check |
|-------|-------|
| "psycopg2 not found" | `pip install psycopg2-binary` on raspibig |
| "DB connection refused" | `psql` test, verify localhost is local to raspibig |
| "No module: deep_translator" | `pip install deep-translator` on raspibig |
| "ANOFM count = 0" | Check if ij_jobs table has data: `psql -c "SELECT COUNT(*) FROM ij_jobs;"` |
| "Cron not running" | `sudo service cron status`, check `/var/log/syslog` for errors |
| "Post didn't publish" | Check `_workspace/03_publisher_output.json` for WP auth errors |

## Cleanup (Optional)

After confirmed working, remove old daily_roundup.py:

```bash
rm /opt/ACTIVE/EVENT_PUBLISHER/daily_roundup_20260603_old.py
```
