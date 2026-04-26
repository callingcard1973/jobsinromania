#!/bin/bash
# deploy_and_run.sh — SCP scripts to raspibig, run both scrapers, report counts
# Run from Windows bash: bash deploy_and_run.sh
set -e

RASPI="tudor@192.168.100.21"
REMOTE_DIR="/opt/ACTIVE/ANR_MADR"
LOCAL_CODE="D:/MEMORY/BUSINESS/IDEAS/ISCIR/ANR_MADR/CODE"
LOCAL_DATA="D:/MEMORY/BUSINESS/IDEAS/ISCIR/ANR_MADR/DATA"

echo "=== ANR+MADR Deploy & Run ==="

# 1. Create remote directory
ssh "$RASPI" "mkdir -p $REMOTE_DIR/CODE $REMOTE_DIR/DATA"

# 2. SCP scripts
echo "[1] Copying scripts to raspibig..."
scp "$LOCAL_CODE/scrape_anr.py" "$RASPI:$REMOTE_DIR/CODE/"
scp "$LOCAL_CODE/scrape_madr_consultanti.py" "$RASPI:$REMOTE_DIR/CODE/"

# 3. Install deps on raspibig (if needed)
echo "[2] Checking dependencies..."
ssh "$RASPI" "pip3 install --quiet pdfplumber requests beautifulsoup4 psycopg2-binary 2>/dev/null || true"

# 4. Patch DB connection in remote copies (raspibig uses localhost:5432)
# Scripts already use localhost:5432 — no patch needed

# 5. Run ANR scraper
echo "[3] Running ANR scraper..."
ssh "$RASPI" "cd $REMOTE_DIR && python3 CODE/scrape_anr.py 2>&1"

# 6. Run MADR scraper
echo "[4] Running MADR scraper..."
ssh "$RASPI" "cd $REMOTE_DIR && python3 CODE/scrape_madr_consultanti.py 2>&1"

# 7. Run email enrichment SQL (raspibig has /tmp/tmp_cui_email.csv)
echo "[5] Running email enrichment SQL..."
ssh "$RASPI" "psql -U tudor -d interjob_master -c \"
-- Load CUI email CSV into temp table
CREATE TEMP TABLE tmp_cui_email (cui TEXT, email TEXT);
COPY tmp_cui_email FROM '/tmp/tmp_cui_email.csv' CSV;

-- Enrich anr_naval by CUI
UPDATE anr_naval n
SET email = t.email
FROM tmp_cui_email t
WHERE n.cui = t.cui
  AND (n.email IS NULL OR n.email = '')
  AND t.email IS NOT NULL;

-- Enrich madr_consultanti by CUI
UPDATE madr_consultanti n
SET email = t.email
FROM tmp_cui_email t
WHERE n.cui = t.cui
  AND (n.email IS NULL OR n.email = '')
  AND t.email IS NOT NULL;

SELECT 'anr_naval' AS tbl, COUNT(*) AS total, COUNT(email) FILTER (WHERE email != '') AS with_email FROM anr_naval
UNION ALL
SELECT 'madr_consultanti', COUNT(*), COUNT(email) FILTER (WHERE email != '') FROM madr_consultanti;
\" 2>&1"

# 8. SCP output CSVs back
echo "[6] Fetching CSVs back to laptop..."
scp "$RASPI:$REMOTE_DIR/DATA/anr_naval.csv" "$LOCAL_DATA/" 2>/dev/null || echo "  anr_naval.csv not found on remote"
scp "$RASPI:$REMOTE_DIR/DATA/madr_consultanti.csv" "$LOCAL_DATA/" 2>/dev/null || echo "  madr_consultanti.csv not found on remote"

echo ""
echo "=== DONE ==="
echo "Check DATA/ for CSVs"
