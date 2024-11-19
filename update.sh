#!/bin/bash

# Script location
SCRIPT_DIR="/home/$USER/YOUR_REPO_NAME"
LOG_FILE="$SCRIPT_DIR/autoupdate.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

# Navigate to script directory
cd "$SCRIPT_DIR"

# Log start of update check
log_message "Checking for updates..."

# Fetch latest changes
git fetch origin main

# Get the revision numbers
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM")

# Check if we need to pull
if [ $LOCAL = $REMOTE ]; then
    log_message "Up-to-date"
elif [ $LOCAL = $BASE ]; then
    log_message "Updates found. Pulling changes..."
    
    # Pull changes
    git pull origin main
    
    # Check if monitor.py exists and is running
    if pgrep -f "python3 monitor.py" > /dev/null; then
        log_message "Restarting monitor..."
        pkill -f "python3 monitor.py"
        nohup python3 monitor.py >> monitor.log 2>&1 &
    else
        log_message "Starting monitor..."
        nohup python3 monitor.py >> monitor.log 2>&1 &
    fi
    
    log_message "Update complete"
else
    log_message "Diverged from origin. Manual intervention required."
fi