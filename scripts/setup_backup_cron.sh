#!/bin/bash
# Setup automated backups for AgentOS
#
# Usage: ./scripts/setup_backup_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Setting up AgentOS backup cron jobs..."

# Create temp crontab
crontab -l 2>/dev/null > /tmp/crontab.tmp || true

# Remove old entries
sed -i '/agentos_backup_gdrive/d' /tmp/crontab.tmp 2>/dev/null || true

# Add daily backup at 2 AM
echo "0 2 * * * cd $PROJECT_DIR && ./scripts/backup_gdrive.sh daily >> /var/log/agentos_backup.log 2>&1 # agentos_backup_gdrive_daily" >> /tmp/crontab.tmp

# Add weekly backup on Sundays at 3 AM
echo "0 3 * * 0 cd $PROJECT_DIR && ./scripts/backup_gdrive.sh weekly >> /var/log/agentos_backup.log 2>&1 # agentos_backup_gdrive_weekly" >> /tmp/crontab.tmp

# Install new crontab
crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

log "Cron jobs installed:"
log "  Daily backup: 2:00 AM"
log "  Weekly backup: 3:00 AM Sundays"
log ""
log "To verify: crontab -l"
log ""
log "Google Drive setup required:"
log "  1. npm install -g gog"
log "  2. gog login your-email@gmail.com"
log "  3. gog drive mkdir 'AgentOS Backups'"
log "  4. gog drive ls 'AgentOS Backups'  # Verify folder exists"
log ""
log "Test manually: ./scripts/backup_gdrive.sh manual"
