#!/bin/bash
# Sync critical data from raspibig to laptop
# Usage: bash sync-raspibig-to-laptop.sh [pull|push|bidirectional]
# Or run as: while true; do ... ; sleep 3600; done

SYNC_TYPE=${1:-pull}
RASPIBIG_HOST="tudor@192.168.100.21"
LAPTOP_PATH="$HOME/MEMORY/BACKUPS/raspibig"
RASPIBIG_PATHS=(
    "/opt/ACTIVE/LOGS/backups"
    "/opt/ACTIVE/PROJECTS"
    "/opt/ACTIVE/INFRA"
)

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

sync_pull() {
    log "PULL: Syncing from raspibig to laptop..."

    # Logs
    rsync -avz --delete "$RASPIBIG_HOST:/opt/ACTIVE/LOGS/backups/" "$LAPTOP_PATH/logs/" 2>/dev/null

    # Critical projects (exclude git, venv, cache)
    rsync -avz --delete --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        "$RASPIBIG_HOST:/opt/ACTIVE/PROJECTS/" "$LAPTOP_PATH/projects/" 2>/dev/null

    # Infrastructure scripts and configs
    rsync -avz --delete --exclude='venv' --exclude='__pycache__' \
        "$RASPIBIG_HOST:/opt/ACTIVE/INFRA/SKILLS/" "$LAPTOP_PATH/scripts/skills/" 2>/dev/null

    log "PULL completed"
}

sync_push() {
    log "PUSH: Syncing from laptop to raspibig..."

    # Push laptop CODE changes to raspibig /opt/ACTIVE mirror
    rsync -avz --delete --exclude='.git' --exclude='venv' --exclude='__pycache__' \
        "$LAPTOP_PATH/../CODE/" "$RASPIBIG_HOST:/opt/ACTIVE/CODE/" 2>/dev/null

    log "PUSH completed"
}

sync_bidirectional() {
    log "BIDIRECTIONAL: Syncing in both directions..."
    sync_pull
    sync_push
    log "BIDIRECTIONAL completed"
}

case $SYNC_TYPE in
    pull)
        sync_pull
        ;;
    push)
        sync_push
        ;;
    bidirectional)
        sync_bidirectional
        ;;
    *)
        log "ERROR: Unknown sync type: $SYNC_TYPE (use: pull, push, bidirectional)"
        exit 1
        ;;
esac
