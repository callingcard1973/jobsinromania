#!/bin/bash
# MERCOSUR Open Data Downloader - Working Sources Only
# Randomized timing to avoid blocks

set -e
cd /opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data

DATE=$(date +%Y%m%d)
LOG="/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/logs/download_${DATE}.log"
mkdir -p /opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/logs

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"
}

# Random delay 1-10 minutes to avoid fixed times
JITTER=$((RANDOM % 600 + 60))
log "Starting with ${JITTER}s jitter"
sleep $JITTER

# === ARGENTINA (WORKING) ===
log "Downloading Argentina INDEC..."
cd argentina
curl -sL "https://www.indec.gob.ar/ftp/cuadros/economia/sh_expo_pais.xls" \
    -o "argentina_exports_${DATE}.xls" 2>/dev/null || true
if [ -s "argentina_exports_${DATE}.xls" ]; then
    log "Argentina: $(wc -c < argentina_exports_${DATE}.xls) bytes"
else
    log "Argentina: FAILED"
fi
sleep $((RANDOM % 30 + 10))

# === URUGUAY (WORKING) ===
log "Downloading Uruguay BCU..."
cd ../uruguay
curl -sL "https://www.bcu.gub.uy/Estadisticas-e-Indicadores/ComercioExterior_ICB/Exportaciones_2024.xlsx" \
    -o "uruguay_exports_${DATE}.xlsx" 2>/dev/null || true
if [ -s "uruguay_exports_${DATE}.xlsx" ]; then
    log "Uruguay: $(wc -c < uruguay_exports_${DATE}.xlsx) bytes"
else
    log "Uruguay: FAILED"
fi
sleep $((RANDOM % 30 + 10))

# === CHILE (WORKING) ===
log "Downloading Chile Aduana..."
cd ../chile
curl -sL "https://www.aduana.cl/exportaciones/prontus_aduana/site/artic/20150527/asocfile/exportaciones_por_producto.xlsx" \
    -o "chile_exports_${DATE}.xlsx" 2>/dev/null || true
if [ -s "chile_exports_${DATE}.xlsx" ]; then
    log "Chile: $(wc -c < chile_exports_${DATE}.xlsx) bytes"
else
    log "Chile: FAILED"
fi
sleep $((RANDOM % 30 + 10))

# === BRAZIL (USE SCRAPERS - OPEN DATA BLOCKED) ===
log "Brazil: Using scrapers (government APIs blocked)"
cd ../brazil

# Run working Brazil scrapers
SCRAPER_DIR="/opt/ACTIVE/IDEAS/MERCOSUR/CLAUDE/OPENCODE/scrapers/mercosur"

# brazil_producers - PASSED tests
timeout 300 python3 "$SCRAPER_DIR/working/brazil_producers.py" --limit 500 \
    --output "brazil_producers_${DATE}.json" 2>/dev/null || true

# connectamericas - PASSED tests
timeout 300 python3 "$SCRAPER_DIR/connectamericas_scraper.py" --limit 500 \
    --output "brazil_connectamericas_${DATE}.json" 2>/dev/null || true

log "Brazil scrapers completed"

# === SUMMARY ===
log "=== DOWNLOAD COMPLETE ==="
cd /opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/data
for country in argentina brazil chile uruguay paraguay; do
    COUNT=$(find $country -name "*${DATE}*" -type f 2>/dev/null | wc -l)
    SIZE=$(du -sh $country 2>/dev/null | cut -f1)
    log "$country: $COUNT new files, $SIZE total"
done

log "Done"
