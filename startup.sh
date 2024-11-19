#!/bin/bash

# Script location
SCRIPT_DIR="/home/nrmaskell/terraforming-mars-monitor"
LOG_FILE="$SCRIPT_DIR/startup.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$1"
}

# Navigate to script directory
cd "$SCRIPT_DIR"

# Start the monitor
log_message "Starting monitor..."
nohup python3 monitor.py >> monitor.log 2>&1 &

# Set up automatic updates every 5 minutes
while true; do
    bash update.sh
    sleep 300  # Wait 5 minutes
done