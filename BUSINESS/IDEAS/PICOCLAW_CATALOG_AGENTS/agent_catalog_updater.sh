#!/bin/bash
# Agent 3: Catalog Updater — regenereaza cataloage HTML si deploy pe A2
# Cron: 0 3 * * 0  (duminica 3 AM)
# Locatie raspibig: /opt/ACTIVE/WEB/CATALOGS/

set -e
SCRIPT_DIR="/opt/ACTIVE/WEB/CATALOGS"
OUTPUT_DIR="/opt/ACTIVE/WEB/CATALOGS/output"
LOG="/opt/LOGS/catalog_updater.log"
TIMESTAMP=$(date +%Y-%m-%d_%H:%M)

echo "[$TIMESTAMP] Catalog Updater START" >> "$LOG"

# 1. Genereaza cataloage din DB
cd "$SCRIPT_DIR"
python3 generate_catalogs_raspibig.py >> "$LOG" 2>&1

# 2. Numara paginile generate
PAGES=$(find "$OUTPUT_DIR" -name "index.html" | wc -l)
DOMAINS=$(ls -d "$OUTPUT_DIR"/*/ 2>/dev/null | wc -l)
echo "[$TIMESTAMP] Generat: $PAGES pagini pe $DOMAINS domenii" >> "$LOG"

# 3. Deploy pe A2 via PHP receiver (nu cPanel token)
for domain_dir in "$OUTPUT_DIR"/*/; do
    domain=$(basename "$domain_dir")
    echo "[$TIMESTAMP] Deploy $domain..." >> "$LOG"

    # Upload fiecare fisier HTML
    find "$domain_dir" -name "*.html" -o -name "*.xml" | while read file; do
        rel_path="${file#$domain_dir}"
        curl -s -X POST "https://$domain/upload_receiver.php" \
            -F "file=@$file" \
            -F "path=$rel_path" \
            -F "key=$DEPLOY_KEY" \
            --max-time 30 >> "$LOG" 2>&1 || true
    done
done

echo "[$TIMESTAMP] Catalog Updater DONE — $PAGES pagini, $DOMAINS domenii" >> "$LOG"

# 4. Submit sitemaps la Google (doar prima data pe luna)
DAY=$(date +%d)
if [ "$DAY" = "01" ]; then
    for domain_dir in "$OUTPUT_DIR"/*/; do
        domain=$(basename "$domain_dir")
        curl -s "https://www.google.com/ping?sitemap=https://$domain/sitemap.xml" >> "$LOG" 2>&1
    done
    echo "[$TIMESTAMP] Sitemaps submitted to Google" >> "$LOG"
fi
