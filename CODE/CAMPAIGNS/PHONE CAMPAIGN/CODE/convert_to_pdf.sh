#!/bin/bash
# Convert Tudor catalog HTML → PDF via WSL Firefox
# Splits large HTML into parts first (skill: html-to-pdf-local)

CATALOG="D:/MEMORY/PHONE CAMPAIGN/CATALOGS/TUDOR/jobs_catalog_april_tudor.html"
OUTDIR="D:/MEMORY/PHONE CAMPAIGN/CATALOGS/TUDOR"

WSL_CATALOG="/mnt/d/MEMORY/PHONE CAMPAIGN/CATALOGS/TUDOR/jobs_catalog_april_tudor.html"
WSL_OUTDIR="/mnt/d/MEMORY/PHONE CAMPAIGN/CATALOGS/TUDOR"

echo "=== Tudor Catalog → PDF ==="
echo "Source: $CATALOG"
SIZE=$(wsl du -m "$WSL_CATALOG" | cut -f1)
echo "File size: ${SIZE}MB"

# Kill any hung Firefox
wsl pkill -9 firefox 2>/dev/null
sleep 2

if [ "$SIZE" -le 2 ]; then
  echo "Converting directly (under 2MB)..."
  wsl bash -c "xvfb-run -a firefox --headless --print-to-file --outdir '/tmp' '$WSL_CATALOG'"
  wsl cp "/tmp/jobs_catalog_april_tudor.pdf" "$WSL_OUTDIR/"
  echo "✓ Done: $OUTDIR/jobs_catalog_april_tudor.pdf"
else
  echo "File is ${SIZE}MB — splitting and converting in parts..."
  python "D:/MEMORY/PHONE CAMPAIGN/CODE/split_catalog.py"

  for PART in "$OUTDIR"/jobs_catalog_april_tudor_part*.html; do
    BASENAME=$(basename "$PART" .html)
    WSL_PART="/mnt/d/MEMORY/PHONE CAMPAIGN/CATALOGS/TUDOR/${BASENAME}.html"
    echo "Converting $BASENAME..."
    wsl pkill -9 firefox 2>/dev/null; sleep 2
    wsl bash -c "xvfb-run -a firefox --headless --print-to-file --outdir '/tmp' '$WSL_PART'"
    wsl cp "/tmp/${BASENAME}.pdf" "$WSL_OUTDIR/"
    echo "  ✓ $BASENAME.pdf"
  done
  echo ""
  echo "✓ All parts done:"
  ls -lh "$OUTDIR"/jobs_catalog_april_tudor_part*.pdf 2>/dev/null
fi
