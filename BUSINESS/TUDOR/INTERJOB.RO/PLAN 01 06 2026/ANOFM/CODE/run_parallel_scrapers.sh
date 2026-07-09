#!/bin/bash
# Parallel ANOFM Scraper - 4 workers with CSV streaming
# Run this on raspibig or raspi

WORKERS=4
TOTAL_PAGES=84
OUTPUT_BASE=/opt/ACTIVE/ANOFM_DATA/csv
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[INFO] Starting $WORKERS parallel workers with phone normalization"

PAGES_PER_WORKER=$((TOTAL_PAGES / WORKERS))
REMAINDER=$((TOTAL_PAGES % WORKERS))
CURRENT_PAGE=1

for i in $(seq 1 $WORKERS); do
    END_PAGE=$((CURRENT_PAGE + PAGES_PER_WORKER - 1))
    if [ $i -le $REMAINDER ]; then
        END_PAGE=$((END_PAGE + 1))
    fi
    OUTPUT_FILE="${OUTPUT_BASE}/worker_${i}_${TIMESTAMP}.csv"
    echo "[INFO] Worker $i: pages $CURRENT_PAGE-$END_PAGE"
    sed "s/page_num = 1/page_num = $CURRENT_PAGE/; s/while True:/while page_num <= $END_PAGE:/" \
        anofm_scraper.py > /tmp/worker_${i}.py
    python3 /tmp/worker_${i}.py --csv --output "$OUTPUT_FILE" &
    CURRENT_PAGE=$((END_PAGE + 1))
done

echo "[INFO] Waiting for workers to complete..."
wait

MERGED_FILE="${OUTPUT_BASE}/anofm_jobs_${TIMESTAMP}.csv"
head -n 1 "${OUTPUT_BASE}/worker_1_${TIMESTAMP}.csv" > "$MERGED_FILE"
for i in $(seq 1 $WORKERS); do
    tail -n +2 "${OUTPUT_BASE}/worker_${i}_${TIMESTAMP}.csv" >> "$MERGED_FILE" 2>/dev/null
done

TOTAL=$(wc -l < "$MERGED_FILE")
echo "[OK] Total $((TOTAL - 1)) jobs with normalized phones saved to $MERGED_FILE"

# Cleanup
rm -f /tmp/worker_*.py "${OUTPUT_BASE}/worker_"*_${TIMESTAMP}.csv

# Link as latest
ln -sf "$MERGED_FILE" "${OUTPUT_BASE}/anofm_jobs_latest.csv"
echo "[INFO] Created symlink: ${OUTPUT_BASE}/anofm_jobs_latest.csv"