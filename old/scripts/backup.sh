#!/bin/bash
# Backup Script - Automated backup system for AI Trading Platform
# Epic 8.5: Backup & Restore
# US-8.5: Backup script with database, config, and algorithm code

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="trading_platform_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_PATH"

log "Starting backup process..."

# Function to backup directory with compression
backup_directory() {
    local source_dir="$1"
    local backup_name="$2"
    
    if [ -d "$source_dir" ]; then
        log "Backing up $source_dir..."
        tar -czf "$BACKUP_PATH/${backup_name}.tar.gz" -C "$(dirname "$source_dir")" "$(basename "$source_dir")"
        log "✓ Backed up $source_dir"
    else
        warning "Directory not found: $source_dir"
    fi
}

# Function to backup individual files
backup_file() {
    local source_file="$1"
    local backup_name="$2"
    
    if [ -f "$source_file" ]; then
        log "Backing up $source_file..."
        cp "$source_file" "$BACKUP_PATH/${backup_name}"
        log "✓ Backed up $source_file"
    else
        warning "File not found: $source_file"
    fi
}

# Backup database
log "=== Backing up Database ==="
backup_directory "$PROJECT_ROOT/data/sqlite" "database"

# Backup configuration files
log "=== Backing up Configuration ==="
backup_directory "$PROJECT_ROOT/config" "config"

# Backup environment file
backup_file "$PROJECT_ROOT/.env" "environment.env"
backup_file "$PROJECT_ROOT/.env.example" "environment.example"

# Backup algorithm code
log "=== Backing up Algorithm Code ==="
backup_directory "$PROJECT_ROOT/algorithms" "algorithms"

# Backup scripts
log "=== Backing up Scripts ==="
backup_directory "$PROJECT_ROOT/scripts" "scripts"

# Backup monitoring code
log "=== Backing up Monitoring ==="
backup_directory "$PROJECT_ROOT/monitoring" "monitoring"

# Create backup manifest
log "=== Creating Backup Manifest ==="
cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "project_root": "$PROJECT_ROOT",
    "backup_path": "$BACKUP_PATH",
    "retention_days": $RETENTION_DAYS,
    "files_backed_up": [
        "database",
        "config",
        "environment.env",
        "environment.example",
        "algorithms",
        "scripts",
        "monitoring"
    ],
    "backup_size_bytes": $(du -sb "$BACKUP_PATH" | cut -f1),
    "backup_size_human": "$(du -sh "$BACKUP_PATH" | cut -f1)",
    "created_by": "backup_script",
    "version": "1.0"
}
EOF

log "✓ Created backup manifest"

# Create compressed archive of entire backup
log "=== Creating Compressed Archive ==="
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
log "✓ Created compressed archive: ${BACKUP_NAME}.tar.gz"

# Calculate checksums for integrity
log "=== Generating Checksums ==="
cd "$BACKUP_DIR"
# Use relative path in checksum file for compatibility
echo "$(sha256sum "${BACKUP_NAME}.tar.gz" | cut -d' ' -f1)  ${BACKUP_NAME}.tar.gz" > "${BACKUP_NAME}.tar.gz.sha256"
log "✓ Generated checksums"

# Clean up uncompressed directory to save space
rm -rf "$BACKUP_PATH"
log "✓ Cleaned up uncompressed backup directory"

# Display backup information
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)
log "=== Backup Complete ==="
log "Backup file: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
log "Backup size: $BACKUP_SIZE"
log "Checksum: $BACKUP_DIR/${BACKUP_NAME}.tar.gz.sha256"

# Cleanup old backups
log "=== Cleaning Up Old Backups ==="
find "$BACKUP_DIR" -name "trading_platform_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "trading_platform_backup_*.tar.gz.sha256" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

OLD_BACKUPS=$(find "$BACKUP_DIR" -name "trading_platform_backup_*.tar.gz" -type f | wc -l)
log "✓ Retained $OLD_BACKUPS recent backups (keeping last $RETENTION_DAYS days)"

# Verify backup integrity
log "=== Verifying Backup Integrity ==="
if sha256sum -c "${BACKUP_NAME}.tar.gz.sha256" --quiet; then
    log "✓ Backup integrity verified"
else
    error "Backup integrity check failed!"
    exit 1
fi

# List current backups
log "=== Current Backups ==="
ls -lah "$BACKUP_DIR"/trading_platform_backup_*.tar.gz 2>/dev/null || log "No backups found"

log "Backup process completed successfully!"
log "Next backup will run automatically via cron job"

# Exit with success
exit 0