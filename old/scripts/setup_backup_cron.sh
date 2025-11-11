#!/bin/bash
# Setup Backup Cron Job - Configure automated daily backups
# Epic 8.5: Backup & Restore
# US-8.5: Automated daily backups

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"

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

# Check if running as root or with sudo
check_permissions() {
    if [ "$EUID" -ne 0 ]; then
        warning "This script should be run as root or with sudo for system-wide cron setup"
        warning "Continuing with user-specific cron setup..."
        return 1
    fi
    return 0
}

# Get current user
get_current_user() {
    if [ -n "$SUDO_USER" ]; then
        echo "$SUDO_USER"
    else
        echo "$(whoami)"
    fi
}

# Setup cron job for specific user
setup_user_cron() {
    local user="$1"
    local cron_schedule="${2:-0 2 * * *}"  # Default: 2 AM daily
    
    log "Setting up backup cron job for user: $user"
    
    # Create cron job entry
    local cron_entry="$cron_schedule $BACKUP_SCRIPT >> $PROJECT_ROOT/logs/backup.log 2>&1"
    
    # Add to user's crontab
    local crontab_file="/var/spool/cron/crontabs/$user"
    if [ -f "$crontab_file" ]; then
        # User has existing crontab
        if ! grep -q "$BACKUP_SCRIPT" "$crontab_file" 2>/dev/null; then
            echo "$cron_entry" | crontab -u "$user" -
            log "✓ Added backup cron job to $user's crontab"
        else
            log "✓ Backup cron job already exists for $user"
        fi
    else
        # Create new crontab
        echo "$cron_entry" | crontab -u "$user" -
        log "✓ Created new crontab for $user with backup job"
    fi
    
    # Ensure log directory exists
    mkdir -p "$PROJECT_ROOT/logs"
    chown "$user" "$PROJECT_ROOT/logs" 2>/dev/null || true
    
    log "✓ Backup cron job configured successfully"
    log "Schedule: $cron_schedule (daily at 2 AM)"
    log "Log file: $PROJECT_ROOT/logs/backup.log"
}

# Setup system-wide cron job
setup_system_cron() {
    log "Setting up system-wide backup cron job"
    
    # Create cron job in /etc/cron.d/
    local cron_file="/etc/cron.d/ai-trading-backup"
    
    cat > "$cron_file" << EOF
# AI Trading Platform - Automated Backup
# Daily backup at 2:00 AM
0 2 * * * $(get_current_user) $BACKUP_SCRIPT >> $PROJECT_ROOT/logs/backup.log 2>&1

# Keep only last 30 days of backups
0 3 * * * $(get_current_user) find $PROJECT_ROOT/backups -name "trading_platform_backup_*.tar.gz" -type f -mtime +30 -delete
EOF
    
    # Set proper permissions
    chmod 644 "$cron_file"
    
    log "✓ System-wide backup cron job created: $cron_file"
    log "Schedule: Daily at 2:00 AM"
    log "Log file: $PROJECT_ROOT/logs/backup.log"
}

# Remove cron job
remove_cron_job() {
    local user="$1"
    
    log "Removing backup cron job for user: $user"
    
    # Remove from user's crontab
    crontab -u "$user" -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" | crontab -u "$user" - 2>/dev/null || true
    
    # Remove system-wide cron file
    local cron_file="/etc/cron.d/ai-trading-backup"
    if [ -f "$cron_file" ]; then
        rm -f "$cron_file"
        log "✓ Removed system-wide cron file: $cron_file"
    fi
    
    log "✓ Backup cron job removed"
}

# Show current cron jobs
show_cron_jobs() {
    local user="$1"
    
    log "Current backup cron jobs for user: $user"
    
    # Check user's crontab
    if crontab -u "$user" -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        echo "User crontab entries:"
        crontab -u "$user" -l 2>/dev/null | grep "$BACKUP_SCRIPT" || true
    else
        echo "No user crontab entries found"
    fi
    
    # Check system-wide cron
    local cron_file="/etc/cron.d/ai-trading-backup"
    if [ -f "$cron_file" ]; then
        echo ""
        echo "System-wide cron entries:"
        cat "$cron_file"
    else
        echo ""
        echo "No system-wide cron entries found"
    fi
}

# Test backup script
test_backup() {
    log "Testing backup script..."
    
    if [ ! -x "$BACKUP_SCRIPT" ]; then
        error "Backup script is not executable: $BACKUP_SCRIPT"
        return 1
    fi
    
    # Run backup in test mode (dry run)
    log "Running backup script test..."
    if "$BACKUP_SCRIPT"; then
        log "✓ Backup script test completed successfully"
        return 0
    else
        error "✗ Backup script test failed"
        return 1
    fi
}

# Display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Setup automated backup cron job for AI Trading Platform"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -u, --user USER         Setup for specific user (default: current user)"
    echo "  -s, --schedule SCHEDULE Cron schedule (default: '0 2 * * *' for 2 AM daily)"
    echo "  -r, --remove            Remove backup cron job"
    echo "  -t, --test              Test backup script"
    echo "  -l, --list              Show current cron jobs"
    echo "  --system                Setup system-wide cron job (requires root)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Setup for current user with default schedule"
    echo "  $0 -u trader            # Setup for user 'trader'"
    echo "  $0 -s '0 3 * * *'       # Setup with custom schedule (3 AM daily)"
    echo "  $0 --remove             # Remove backup cron job"
    echo "  $0 --test               # Test backup script"
    echo "  $0 --system             # Setup system-wide (requires root)"
}

# Main execution
USER=""
SCHEDULE="0 2 * * *"
REMOVE=false
TEST=false
LIST=false
SYSTEM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -s|--schedule)
            SCHEDULE="$2"
            shift 2
            ;;
        -r|--remove)
            REMOVE=true
            shift
            ;;
        -t|--test)
            TEST=true
            shift
            ;;
        -l|--list)
            LIST=true
            shift
            ;;
        --system)
            SYSTEM=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Set default user if not specified
if [ -z "$USER" ]; then
    USER=$(get_current_user)
fi

# Handle different operations
if [ "$TEST" = true ]; then
    test_backup
    exit $?
fi

if [ "$LIST" = true ]; then
    show_cron_jobs "$USER"
    exit 0
fi

if [ "$REMOVE" = true ]; then
    remove_cron_job "$USER"
    exit 0
fi

# Setup cron job
if [ "$SYSTEM" = true ]; then
    if ! check_permissions; then
        error "System-wide setup requires root privileges"
        exit 1
    fi
    setup_system_cron
else
    setup_user_cron "$USER" "$SCHEDULE"
fi

log "Backup automation setup completed!"
log ""
log "Next steps:"
log "1. Test the backup: $0 --test"
log "2. Monitor backup logs: tail -f $PROJECT_ROOT/logs/backup.log"
log "3. List backups: $PROJECT_ROOT/scripts/restore.sh --list"
log "4. Manual backup: $BACKUP_SCRIPT"

exit 0