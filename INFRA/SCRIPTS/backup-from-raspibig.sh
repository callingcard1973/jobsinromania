#!/bin/bash
# Backup critical data from raspibig to laptop
# Usage: bash backup-from-raspibig.sh [all|logs|db|projects]

BACKUP_TYPE=${1:-all}
BACKUP_DIR="/opt/ACTIVE/LOGS/backups"
LAPTOP_USER="apami"
LAPTOP_HOST="192.168.100.25"
LAPTOP_PATH="D:/MEMORY/BACKUPS/raspibig"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$BACKUP_DIR/cron.log"
}

backup_logs() {
    log "Backing up logs..."
    tar -czf "$BACKUP_DIR/logs_$TIMESTAMP.tar.gz" /opt/ACTIVE/LOGS --exclude=backups 2>/dev/null
    scp -q "$BACKUP_DIR/logs_$TIMESTAMP.tar.gz" "$LAPTOP_USER@$LAPTOP_HOST:$LAPTOP_PATH/logs/" 2>/dev/null && log "Logs backed up" || log "WARNING: Log backup to laptop failed"
}

backup_db() {
    log "Backing up PostgreSQL..."
    pg_dump -h localhost -U tudor interjob_master | gzip > "$BACKUP_DIR/interjob_master_$TIMESTAMP.sql.gz" 2>/dev/null
    log "DB dump created: interjob_master_$TIMESTAMP.sql.gz"
    scp -q "$BACKUP_DIR/interjob_master_$TIMESTAMP.sql.gz" "$LAPTOP_USER@$LAPTOP_HOST:$LAPTOP_PATH/db/" 2>/dev/null || log "WARNING: DB backup to laptop failed"
}

backup_projects() {
    log "Backing up PROJECTS directory..."
    tar -czf "$BACKUP_DIR/projects_$TIMESTAMP.tar.gz" /opt/ACTIVE/PROJECTS --exclude=.git 2>/dev/null
    scp -q "$BACKUP_DIR/projects_$TIMESTAMP.tar.gz" "$LAPTOP_USER@$LAPTOP_HOST:$LAPTOP_PATH/projects/" 2>/dev/null && log "Projects backed up" || log "WARNING: Projects backup to laptop failed"
}

cleanup() {
    log "Cleaning up old backups (>7 days)..."
    find "$BACKUP_DIR" -name "*.tar.gz" -o -name "*.sql.gz" | xargs -I {} sh -c 'test $(( ($(date +%s) - $(stat -c %Y {})) / 86400 )) -gt 7 && rm {} && echo "Removed: {}"' 2>/dev/null
}

case $BACKUP_TYPE in
    all)
        backup_logs
        backup_db
        backup_projects
        cleanup
        log "Full backup completed"
        ;;
    logs)
        backup_logs
        ;;
    db)
        backup_db
        ;;
    projects)
        backup_projects
        ;;
    *)
        log "ERROR: Unknown backup type: $BACKUP_TYPE"
        exit 1
        ;;
esac
