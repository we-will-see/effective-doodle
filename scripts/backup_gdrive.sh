#!/bin/bash
# Google Drive backup script for AgentOS
# Requires: gog CLI configured with Google account
#
# Setup:
#   npm i -g gog
#   gog login your-email@gmail.com
#   # Create folder manually: gog drive mkdir "AgentOS Backups"
#
# Usage:
#   ./scripts/backup_gdrive.sh [daily|weekly|manual]

set -euo pipefail

BACKUP_TYPE="${1:-manual}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/backups"
GDRIVE_FOLDER=${GDRIVE_FOLDER:-"AgentOS Backups"}
DB_NAME="agentos"
DB_USER="agentos"
DB_HOST="localhost"
RETENTION_DAYS=30

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$BACKUP_DIR/backup.log"
}

# Check if gog is configured
check_gog() {
    if ! command -v gog &> /dev/null; then
        log "ERROR: gog CLI not found"
        log "Install with: npm i -g gog"
        exit 1
    fi
    
    local email
    email=$(gog whoami --plain 2>/dev/null | head -1 || echo "")
    if [[ -z "$email" ]]; then
        log "ERROR: Not logged in to Google"
        log "Run: gog login your-email@gmail.com"
        exit 1
    fi
    
    log "Google Drive authenticated: $email"
}

# Find Google Drive folder ID
get_folder_id() {
    local folder_name="$1"
    local folder_id
    
    # Try to find existing folder
    folder_id=$(gog drive search "$folder_name" --json 2>/dev/null | jq -r '.files[0].id' 2>/dev/null || echo "")
    
    if [[ -z "$folder_id" || "$folder_id" == "null" ]]; then
        log "WARNING: Folder '$folder_name' not found in Google Drive"
        log "Create it with: gog drive mkdir \"$folder_name\""
        exit 1
    fi
    
    echo "$folder_id"
}

# Create backup
BACKUP_FILE="$BACKUP_DIR/agentos_backup_${BACKUP_TYPE}_${DATE}.sql.gz"
MANIFEST_FILE="$BACKUP_DIR/agentos_backup_${BACKUP_TYPE}_${DATE}.manifest.json"

log "Starting $BACKUP_TYPE backup..."

# Verify gog
check_gog

# Dump database
log "Creating database dump..."
pg_dump \
    --host="$DB_HOST" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --verbose \
    2>&1 | gzip > "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Backup created: $FILE_SIZE"

# Get checksums
MD5=$(md5sum "$BACKUP_FILE" | cut -d' ' -f1)
SHA256=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)

# Create manifest
cat > "$MANIFEST_FILE" << EOF
{
  "backup_type": "$BACKUP_TYPE",
  "backup_date": "$DATE",
  "db_name": "$DB_NAME",
  "file_size": "$FILE_SIZE",
  "checksum_md5": "$MD5",
  "checksum_sha256": "$SHA256",
  "retention_days": $RETENTION_DAYS
}
EOF

log "Manifest created"

# Find target folder
log "Locating Google Drive folder: $GDRIVE_FOLDER"
FOLDER_ID=$(get_folder_id "$GDRIVE_FOLDER")
log "Target folder ID: $FOLDER_ID"

# Create dated subfolder
log "Creating backup folder..."
BACKUP_FOLDER_ID=$(gog drive mkdir "${DATE}_${BACKUP_TYPE}" --parent "$FOLDER_ID" --json 2>/dev/null | jq -r '.id' || echo "")
if [[ -z "$BACKUP_FOLDER_ID" || "$BACKUP_FOLDER_ID" == "null" ]]; then
    # Fall back to using parent folder
    BACKUP_FOLDER_ID="$FOLDER_ID"
    log "Using parent folder"
else
    log "Created backup folder: $BACKUP_FOLDER_ID"
fi

# Upload files to Google Drive
log "Uploading backup file to Google Drive..."
gog drive upload "$BACKUP_FILE" \
    --dest-folder "$BACKUP_FOLDER_ID" \
    --rename "agentos_backup_${BACKUP_TYPE}_${DATE}.sql.gz"

log "Uploading manifest..."
gog drive upload "$MANIFEST_FILE" \
    --dest-folder "$BACKUP_FOLDER_ID" \
    --rename "agentos_backup_${BACKUP_TYPE}_${DATE}.manifest.json"

log "Google Drive upload complete"

# Cleanup old local backups
log "Cleaning up old backups (> $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "agentos_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "agentos_backup_*.manifest.json" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

log "Backup process completed successfully"
exit 0
