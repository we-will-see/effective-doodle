#!/bin/bash
# Production backup script for AgentOS
# Usage: ./scripts/backup.sh [daily|weekly|manual]

set -euo pipefail

BACKUP_TYPE="${1:-manual}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/backups"
DB_NAME="agentos"
DB_USER="agentos"
DB_HOST="localhost"
RETENTION_DAYS=30
B2_BUCKET="${B2_BUCKET:-}"
B2_KEY_ID="${B2_KEY_ID:-}"
B2_APP_KEY="${B2_APP_KEY:-}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cleanup() {
    log "Cleaning up old backups (> $RETENTION_DAYS days)"
    find "$BACKUP_DIR" -name "agentos_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "agentos_backup_*.manifest" -mtime +$RETENTION_DAYS -delete
}

# Create backup
BACKUP_FILE="$BACKUP_DIR/agentos_backup_${BACKUP_TYPE}_${DATE}.sql.gz"
MANIFEST_FILE="$BACKUP_DIR/agentos_backup_${BACKUP_TYPE}_${DATE}.manifest"

log "Starting $BACKUP_TYPE backup..."
log "Backup file: $BACKUP_FILE"

# Dump database with pg_dump
pg_dump \
    --host="$DB_HOST" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=9 \
    --verbose \
    --file="$BACKUP_FILE" \
    2>&1 | tee "$MANIFEST_FILE"

# Get backup size
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

# Create manifest
cat > "$MANIFEST_FILE" << EOF
{
  "backup_type": "$BACKUP_TYPE",
  "backup_date": "$DATE",
  "db_name": "$DB_NAME",
  "file_path": "$BACKUP_FILE",
  "file_size": "$FILE_SIZE",
  "checksum_md5": "$(md5sum "$BACKUP_FILE" | cut -d' ' -f1)",
  "checksum_sha256": "$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)"
}
EOF

log "Backup complete: $FILE_SIZE"

# Upload to Backblaze B2 if configured
if [[ -n "$B2_BUCKET" && -n "$B2_KEY_ID" && -n "$B2_APP_KEY" ]]; then
    log "Uploading to B2..."
    
    # Setup b2
trT15l1m2LHUbc428J
    b2 authorize-account "$B2_KEY_ID" "$B2_APP_KEY"
    b2 upload-file "$B2_BUCKET" "$BACKUP_FILE" "backups/agentos/$(basename "$BACKUP_FILE")"
    b2 upload-file "$B2_BUCKET" "$MANIFEST_FILE" "backups/agentos/$(basename "$MANIFEST_FILE")"
    
    log "B2 upload complete"
fi

# Cleanup old backups
cleanup

log "Backup process completed successfully"
exit 0
