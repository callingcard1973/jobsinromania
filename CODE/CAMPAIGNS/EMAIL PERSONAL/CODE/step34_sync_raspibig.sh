#!/bin/bash
# Step 34: Sync enriched companies_clean to raspibig
# Dumps selected tables from laptop PG18 → SCP → restore on raspibig PG

set -e

PGBIN="/c/Program Files/PostgreSQL/18/bin"
PGPASSWORD=tudor
export PGPASSWORD

TABLES=(
  "companies_clean"
  "master_emails"
  "dnc_list"
)

DUMP_DIR="D:/MEMORY/EMAIL PERSONAL"
RASPI="tudor@192.168.100.21"
RASPI_DIR="/opt/ACTIVE/DB_SYNC"

echo "=== Dumping tables from laptop ==="
for TABLE in "${TABLES[@]}"; do
  echo "Dumping $TABLE..."
  "$PGBIN/pg_dump.exe" \
    -U tudor -h 127.0.0.1 -p 5433 \
    -d interjob_master \
    -t "$TABLE" \
    --data-only --column-inserts \
    -f "$DUMP_DIR/${TABLE}_sync.sql"
  echo "  Done: $DUMP_DIR/${TABLE}_sync.sql"
done

echo ""
echo "=== SCP to raspibig ==="
ssh "$RASPI" "mkdir -p $RASPI_DIR"
for TABLE in "${TABLES[@]}"; do
  scp "$DUMP_DIR/${TABLE}_sync.sql" "$RASPI:$RASPI_DIR/"
  echo "  Uploaded: ${TABLE}_sync.sql"
done

echo ""
echo "=== Restore on raspibig ==="
ssh "$RASPI" "
  for f in $RASPI_DIR/*_sync.sql; do
    echo \"Restoring \$f...\"
    psql -U tudor -d interjob_master -f \"\$f\" 2>&1 | tail -3
  done
  echo 'Sync complete'
"
