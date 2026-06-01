#!/bin/bash
# Daily build: extract jobs → build HTML → deploy to GitHub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/build.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== JobsInRomania Daily Build ==="

# Step 1: Extract Romania jobs from PostgreSQL
log "Step 1: Extracting ANOFM Romania jobs..."
if python3 "${SCRIPT_DIR}/generate_romania_jobs.py" >> "$LOG_FILE" 2>&1; then
    log "✓ Jobs extracted"
else
    log "✗ Failed to extract jobs"
    exit 1
fi

# Step 2: Build static HTML pages
log "Step 2: Building HTML pages..."
if python3 "${SCRIPT_DIR}/build_romania_pages.py" >> "$LOG_FILE" 2>&1; then
    log "✓ Pages built"
else
    log "✗ Failed to build pages"
    exit 1
fi

# Step 3: Deploy to GitHub
log "Step 3: Deploying to GitHub..."
if python3 "${SCRIPT_DIR}/deploy_github.py" >> "$LOG_FILE" 2>&1; then
    log "✓ Deployed to GitHub"
else
    log "✗ Failed to deploy"
    exit 1
fi

log "=== Build complete ==="
