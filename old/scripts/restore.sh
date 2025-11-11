#!/bin/bash
# Restore Script - Restore system for AI Trading Platform
# Epic 8.5: Backup & Restore
# US-8.5: Restore script with validation and rollback capability

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS] <backup_file>"
    echo ""
    echo "Restore AI Trading Platform from backup"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -l, --list              List available backups"
    echo "  -d, --dry-run           Show what would be restored without actually restoring"
    echo "  -f, --force             Force restore without confirmation"
    echo "  -t, --target-dir DIR    Restore to specific directory (default: $PROJECT_ROOT)"
    echo "  --verify-only           Only verify backup integrity without restoring"
    echo ""
    echo "Examples:"
    echo "  $0 --list                           # List available backups"
    echo "  $0 --dry-run backup_file.tar.gz     # Preview restore"
    echo "  $0 backup_file.tar.gz               # Interactive restore"
    echo "  $0 --force backup_file.tar.gz       # Force restore without confirmation"
}

# Function to list available backups
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    echo ""
    
    if [ ! -d "$BACKUP_DIR" ]; then
        warning "Backup directory not found: $BACKUP_DIR"
        return 1
    fi
    
    local count=0
    for backup_file in "$BACKUP_DIR"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            local filename=$(basename "$backup_file")
            local size=$(du -h "$backup_file" | cut -f1)
            local date=$(stat -c %y "$backup_file" | cut -d' ' -f1)
            local checksum_file="${backup_file}.sha256"
            
            echo "[$((++count))] $filename"
            echo "    Size: $size"
            echo "    Date: $date"
            
            if [ -f "$checksum_file" ]; then
                if sha256sum -c "$checksum_file" --quiet 2>/dev/null; then
                    echo "    Integrity: ✓ Verified"
                else
                    echo "    Integrity: ✗ Failed"
                fi
            else
                echo "    Integrity: ? No checksum"
            fi
            echo ""
        fi
    done
    
    if [ $count -eq 0 ]; then
        warning "No backups found in $BACKUP_DIR"
        return 1
    fi
    
    return 0
}

# Function to verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    log "Verifying backup integrity: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    local checksum_file="${backup_file}.sha256"
    
    if [ -f "$checksum_file" ]; then
        # Change to the directory containing the backup file for checksum verification
        local backup_dir=$(dirname "$backup_file")
        local backup_name=$(basename "$backup_file")
        
        if (cd "$backup_dir" && sha256sum -c "${backup_name}.sha256" --quiet); then
            log "✓ Backup integrity verified"
            return 0
        else
            error "✗ Backup integrity check failed!"
            return 1
        fi
    else
        warning "No checksum file found: $checksum_file"
        warning "Cannot verify backup integrity"
        return 1
    fi
}

# Function to extract and preview backup contents
preview_backup() {
    local backup_file="$1"
    local target_dir="$2"
    
    log "Previewing backup contents: $backup_file"
    echo ""
    
    # Create temporary directory for preview
    local temp_dir=$(mktemp -d)
    
    # Extract backup to temporary directory
    if tar -tzf "$backup_file" >/dev/null 2>&1; then
        tar -xzf "$backup_file" -C "$temp_dir" 2>/dev/null || {
            error "Failed to extract backup for preview"
            rm -rf "$temp_dir"
            return 1
        }
        
        # Show directory structure
        log "Backup contents:"
        find "$temp_dir" -type f | head -20 | while read file; do
            local relative_path="${file#$temp_dir/}"
            echo "  $relative_path"
        done
        
        local total_files=$(find "$temp_dir" -type f | wc -l)
        if [ $total_files -gt 20 ]; then
            echo "  ... and $((total_files - 20)) more files"
        fi
        
        echo ""
        log "Total files in backup: $total_files"
        
        # Show manifest if available
        local manifest_file="$temp_dir"/*/manifest.json
        if [ -f "$manifest_file" ]; then
            log "Backup manifest:"
            cat "$manifest_file" | python3 -m json.tool 2>/dev/null || cat "$manifest_file"
        fi
        
        # Cleanup
        rm -rf "$temp_dir"
        
    else
        error "Invalid backup file or corrupted archive"
        return 1
    fi
}

# Function to create backup before restore
create_pre_restore_backup() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local pre_backup_dir="$PROJECT_ROOT/pre_restore_backup_$timestamp"
    
    log "Creating pre-restore backup: $pre_backup_dir"
    
    # Backup critical directories
    mkdir -p "$pre_backup_dir"
    
    # Backup database
    if [ -d "$PROJECT_ROOT/data/sqlite" ]; then
        cp -r "$PROJECT_ROOT/data/sqlite" "$pre_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup config
    if [ -d "$PROJECT_ROOT/config" ]; then
        cp -r "$PROJECT_ROOT/config" "$pre_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup algorithms
    if [ -d "$PROJECT_ROOT/algorithms" ]; then
        cp -r "$PROJECT_ROOT/algorithms" "$pre_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup scripts
    if [ -d "$PROJECT_ROOT/scripts" ]; then
        cp -r "$PROJECT_ROOT/scripts" "$pre_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup monitoring
    if [ -d "$PROJECT_ROOT/monitoring" ]; then
        cp -r "$PROJECT_ROOT/monitoring" "$pre_backup_dir/" 2>/dev/null || true
    fi
    
    log "✓ Pre-restore backup created: $pre_backup_dir"
    echo "$pre_backup_dir"
}

# Function to restore from backup
restore_backup() {
    local backup_file="$1"
    local target_dir="$2"
    local force="$3"
    
    log "Starting restore process..."
    log "Backup file: $backup_file"
    log "Target directory: $target_dir"
    
    # Verify backup integrity
    if ! verify_backup "$backup_file"; then
        error "Backup verification failed. Aborting restore."
        return 1
    fi
    
    # Create pre-restore backup
    local pre_backup_dir=$(create_pre_restore_backup)
    
    # Confirm restore unless force flag is set
    if [ "$force" != "true" ]; then
        echo ""
        warning "This will overwrite existing files in $target_dir"
        warning "A backup of your current system has been created at: $pre_backup_dir"
        echo ""
        read -p "Do you want to continue with the restore? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log "Restore cancelled by user"
            return 0
        fi
    fi
    
    # Create target directory if it doesn't exist
    mkdir -p "$target_dir"
    
    # Extract backup
    log "Extracting backup..."
    if tar -xzf "$backup_file" -C "$target_dir" --strip-components=1; then
        log "✓ Backup extracted successfully"
    else
        error "Failed to extract backup"
        return 1
    fi
    
    # Set proper permissions
    log "Setting permissions..."
    find "$target_dir" -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    find "$target_dir" -type d -exec chmod 755 {} \; 2>/dev/null || true
    
    # Verify restore
    log "Verifying restore..."
    local restored_files=0
    for dir in database config algorithms scripts monitoring; do
        if [ -d "$target_dir/$dir" ]; then
            log "✓ Restored: $dir"
            ((restored_files++))
        else
            warning "Not found in backup: $dir"
        fi
    done
    
    log "=== Restore Complete ==="
    log "Restored $restored_files components"
    log "Pre-restore backup available at: $pre_backup_dir"
    log "You may need to restart services after restore"
    
    return 0
}

# Parse command line arguments
DRY_RUN=false
FORCE=false
TARGET_DIR="$PROJECT_ROOT"
VERIFY_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -t|--target-dir)
            TARGET_DIR="$2"
            shift 2
            ;;
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Main execution
if [ "$VERIFY_ONLY" = true ]; then
    if [ -z "$BACKUP_FILE" ]; then
        error "Backup file required for verification"
        usage
        exit 1
    fi
    
    # Convert relative path to absolute
    if [[ ! "$BACKUP_FILE" =~ ^/ ]]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    fi
    
    verify_backup "$BACKUP_FILE"
    exit $?
fi

if [ -z "$BACKUP_FILE" ]; then
    # No backup file specified, show usage and list backups
    usage
    echo ""
    log "Available backups:"
    list_backups
    exit 0
fi

# Convert relative path to absolute
if [[ ! "$BACKUP_FILE" =~ ^/ ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    echo ""
    log "Available backups:"
    list_backups
    exit 1
fi

# Handle different modes
if [ "$DRY_RUN" = true ]; then
    preview_backup "$BACKUP_FILE" "$TARGET_DIR"
else
    restore_backup "$BACKUP_FILE" "$TARGET_DIR" "$FORCE"
fi

exit $?