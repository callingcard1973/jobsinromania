# PostgreSQL Automated Backup System

Comprehensive automated backup solution for raspibig PostgreSQL infrastructure with 113GB+ databases.

## Features

- **Full Database Dumps**: Complete backup of all production databases
- **Intelligent Compression**: Gzip compression with configurable levels (6-9)
- **7-4-12 Retention Policy**: 7 daily, 4 weekly, 12 monthly backups
- **Integrity Verification**: MD5 hashing, gzip integrity, SQL syntax validation
- **Telegram Notifications**: Success/failure alerts with detailed reports
- **Storage Management**: Automatic cleanup of expired backups
- **Recovery Testing**: Optional backup restoration verification
- **Systemd Integration**: Automated daily execution at 2:30 AM

## Architecture

```
/opt/ACTIVE/INFRA/BACKUPS/
├── postgresql_backup.py        # Main backup orchestrator
├── postgresql_rotation.py      # Backup retention management
├── postgresql_verify.py        # Integrity verification
├── setup_postgresql_backup.py  # System setup and management
├── postgresql-backup.service   # Systemd service definition
├── postgresql-backup.timer     # Systemd timer configuration
└── README.md                   # This documentation

/opt/BACKUPS/postgresql/
├── interjob_master_2026-04-04_02-30.sql.gz
├── norway_emails_2026-04-04_02-30.sql.gz
├── backup_state.json
└── rotation_state.json
```

## Database Coverage

| Database | Priority | Compression | Size Est. |
|----------|----------|-------------|-----------|
| `interjob_master` | Critical | Level 6 | 113 GB → ~15 GB |
| `norway_emails` | High | Level 9 | 2.1 GB → ~300 MB |
| `denmark_emails` | High | Level 9 | 800 MB → ~120 MB |
| `email_sender` | High | Level 9 | 500 MB → ~75 MB |
| `anofm` | Medium | Level 9 | 1.5 GB → ~225 MB |
| `bulgaria_emails` | Medium | Level 9 | 300 MB → ~45 MB |
| `eu_funds_bg` | Medium | Level 9 | 200 MB → ~30 MB |
| `romania_emails` | Medium | Level 9 | 400 MB → ~60 MB |

**Total Estimated Daily Backup Size**: ~16 GB compressed

## Installation

### 1. Initial Setup

```bash
# Run complete system setup
sudo python3 /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py setup
```

### 2. Manual Installation Steps

```bash
# Create backup directory
sudo mkdir -p /opt/BACKUPS/postgresql
sudo chown tudor:tudor /opt/BACKUPS/postgresql

# Install systemd service files
sudo cp /opt/ACTIVE/INFRA/BACKUPS/postgresql-backup.service /etc/systemd/system/
sudo cp /opt/ACTIVE/INFRA/BACKUPS/postgresql-backup.timer /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable postgresql-backup.timer
sudo systemctl start postgresql-backup.timer
```

### 3. Environment Variables

```bash
# Required for Telegram notifications
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="-1002157155407"  # Default: raspibig monitoring channel
```

## Usage

### Manual Backup Operations

```bash
# Backup all databases
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py

# Backup specific databases
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py --databases interjob_master norway_emails

# Backup only critical databases
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py --critical-only

# Dry run (show what would be backed up)
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py --dry-run

# Skip verification (faster)
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py --no-verify
```

### Rotation Management

```bash
# Apply retention policy (delete old backups)
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_rotation.py

# Dry run rotation (show what would be deleted)
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_rotation.py --dry-run
```

### Verification and Recovery

```bash
# Verify all recent backups
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_verify.py

# Verify specific backup file
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_verify.py --file /opt/BACKUPS/postgresql/interjob_master_2026-04-04_02-30.sql.gz

# Include recovery testing (slow)
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_verify.py --recovery-test

# Verify only backups from last 3 days
python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_verify.py --max-age 3
```

### System Management

```bash
# Check system status
python3 /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py status

# Run system tests
python3 /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py test

# Start/stop backup timer
python3 /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py start
python3 /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py stop
```

## Systemd Service Management

```bash
# Check service status
systemctl status postgresql-backup.timer
systemctl status postgresql-backup.service

# View recent logs
journalctl -u postgresql-backup.timer -f
journalctl -u postgresql-backup.service --since "1 hour ago"

# Manual backup trigger
systemctl start postgresql-backup.service

# Enable/disable automatic backups
systemctl enable postgresql-backup.timer   # Enable
systemctl disable postgresql-backup.timer  # Disable
```

## Recovery Procedures

### 1. Full Database Recovery

```bash
# Stop services using the database
sudo systemctl stop your-app-services

# Drop existing database (CAREFUL!)
dropdb -U tudor -h localhost database_name

# Create new database
createdb -U tudor -h localhost database_name

# Restore from backup
gunzip -c /opt/BACKUPS/postgresql/database_name_YYYY-MM-DD_HH-MM.sql.gz | \
psql -U tudor -h localhost -d database_name

# Restart services
sudo systemctl start your-app-services
```

### 2. Partial Recovery (Specific Tables)

```bash
# Extract specific table from backup
gunzip -c backup.sql.gz | grep -A 10000 "CREATE TABLE table_name" > table_restore.sql

# Apply to database
psql -U tudor -h localhost -d database_name -f table_restore.sql
```

### 3. Point-in-Time Recovery

```bash
# Find backup closest to desired time
ls -la /opt/BACKUPS/postgresql/ | grep database_name

# Restore and apply subsequent changes manually
# (Requires additional WAL archiving for true PITR)
```

## Monitoring and Alerts

### Telegram Notifications

- **Success**: Daily backup completion summary
- **Warnings**: Partial failures with details
- **Errors**: Complete backup failures with diagnostics
- **Recovery**: Test recovery results

### Log Files

```bash
# Main backup logs
tail -f /opt/ACTIVE/INFRA/LOGS/postgresql_backup.log

# Rotation logs
tail -f /opt/ACTIVE/INFRA/LOGS/postgresql_rotation.log

# Verification logs
tail -f /opt/ACTIVE/INFRA/LOGS/postgresql_verify.log

# Systemd service logs
journalctl -u postgresql-backup.service -f
```

### State Files

```bash
# Backup state and metadata
cat /opt/BACKUPS/postgresql/backup_state.json

# Rotation policy application
cat /opt/BACKUPS/postgresql/rotation_state.json

# Verification results
cat /opt/BACKUPS/postgresql/verification_report.json
```

## Storage Requirements

### Disk Space Planning

- **Daily Backups**: ~16 GB compressed
- **Weekly Retention**: 7 × 16 GB = ~112 GB
- **Monthly Retention**: Additional ~48 GB (weekly + monthly)
- **Safety Buffer**: 50 GB for temporary operations
- **Total Required**: ~210 GB minimum

### Current Status (Example)

```bash
# Check backup directory size
du -sh /opt/BACKUPS/postgresql/

# Check available disk space
df -h /opt

# Check individual backup sizes
ls -lh /opt/BACKUPS/postgresql/*.sql.gz
```

## Performance Characteristics

### Backup Times (Estimated)

- **interjob_master (113 GB)**: 45-60 minutes
- **norway_emails (2.1 GB)**: 3-5 minutes
- **Other databases**: 1-3 minutes each
- **Total Session**: 60-75 minutes

### Compression Ratios

- **Text/CSV data**: 85-90% compression
- **Binary data**: 50-70% compression
- **Mixed workloads**: 80-85% compression

### Resource Usage

- **CPU**: Up to 80% during compression
- **Memory**: Up to 4GB for large databases
- **I/O**: Sequential writes, minimal impact
- **Network**: Local connections only

## Troubleshooting

### Common Issues

1. **Backup Failures**
   ```bash
   # Check database connectivity
   psql -U tudor -h localhost -d database_name -c "SELECT version();"
   
   # Check disk space
   df -h /opt
   
   # Check permissions
   ls -la /opt/BACKUPS/postgresql/
   ```

2. **Service Won't Start**
   ```bash
   # Check service definition
   systemctl cat postgresql-backup.service
   
   # Check timer configuration
   systemctl cat postgresql-backup.timer
   
   # Reset failed state
   systemctl reset-failed postgresql-backup.service
   ```

3. **Verification Failures**
   ```bash
   # Check backup file integrity
   gunzip -t /opt/BACKUPS/postgresql/backup_file.sql.gz
   
   # Verify MD5 hash manually
   md5sum /opt/BACKUPS/postgresql/backup_file.sql.gz
   ```

4. **Storage Issues**
   ```bash
   # Clean old backups manually
   find /opt/BACKUPS/postgresql/ -name "*.sql.gz" -mtime +30 -delete
   
   # Force rotation
   python3 /opt/ACTIVE/INFRA/BACKUPS/postgresql_rotation.py
   ```

### Emergency Procedures

1. **Disable Automatic Backups**
   ```bash
   sudo systemctl stop postgresql-backup.timer
   sudo systemctl disable postgresql-backup.timer
   ```

2. **Emergency Space Recovery**
   ```bash
   # Remove oldest backups
   ls -t /opt/BACKUPS/postgresql/*.sql.gz | tail -10 | xargs rm -f
   ```

3. **Manual Recovery Test**
   ```bash
   # Create test database and restore
   createdb -U tudor test_recovery_db
   gunzip -c backup.sql.gz | psql -U tudor -d test_recovery_db
   dropdb -U tudor test_recovery_db
   ```

## Maintenance

### Weekly Tasks

- Review backup success rates
- Check disk space utilization
- Verify recent backup integrity
- Update retention policy if needed

### Monthly Tasks

- Test full recovery procedure
- Archive old verification reports
- Review and update documentation
- Performance optimization review

### Quarterly Tasks

- Disaster recovery drill
- Security audit of backup files
- Capacity planning review
- System performance benchmarking

## Security Considerations

- Backup files contain sensitive data
- Restrict access to `tudor` user and backup operators
- Consider encryption for long-term storage
- Regular security audits of backup procedures
- Network isolation for backup operations

## Contact and Support

- **Primary Contact**: tudor@raspibig (SSH: 192.168.100.21)
- **Telegram Alerts**: @raspibig_controller_bot
- **Documentation**: `/opt/ACTIVE/INFRA/BACKUPS/README.md`
- **Log Analysis**: `/opt/ACTIVE/INFRA/LOGS/postgresql_*.log`