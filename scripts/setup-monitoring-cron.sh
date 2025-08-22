#!/bin/bash

# API Monitoring Cron Setup Script
# Purpose: 프로젝트 내에서 API 모니터링을 위한 cron job 설정
# Version: 1.0.0

set -euo pipefail

readonly SCRIPT_DIR=$(dirname "$0")
readonly PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")
readonly API_MONITOR_SCRIPT="$PROJECT_ROOT/scripts/api-monitor.sh"
readonly LOG_DIR="$PROJECT_ROOT/logs"

echo "🔧 Setting up API monitoring cron job"
echo "Project root: $PROJECT_ROOT"
echo "Monitor script: $API_MONITOR_SCRIPT"
echo "Log directory: $LOG_DIR"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Make sure the monitoring script is executable
chmod +x "$API_MONITOR_SCRIPT"

# Create cron job entry
CRON_ENTRY="*/5 * * * * cd $PROJECT_ROOT && API_MONITOR_LOG_DIR=./logs ./scripts/api-monitor.sh monitor >> $LOG_DIR/cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "api-monitor.sh"; then
    echo "⚠️  Existing cron job found. Removing old entry..."
    crontab -l 2>/dev/null | grep -v "api-monitor.sh" | crontab -
fi

# Add new cron job
echo "✅ Adding cron job..."
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "🚀 Cron job setup complete!"
echo "   Schedule: Every 5 minutes"
echo "   Command: $CRON_ENTRY"
echo "   Logs: $LOG_DIR/api-monitoring.log"
echo "   Cron logs: $LOG_DIR/cron.log"

# Show current crontab
echo
echo "Current crontab entries:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" || echo "No crontab entries found"

# Test the monitoring script once
echo
echo "🧪 Testing monitoring script..."
cd "$PROJECT_ROOT"
API_MONITOR_LOG_DIR=./logs ./scripts/api-monitor.sh monitor

echo
echo "✅ Setup complete! Monitoring will run every 5 minutes."
echo "📊 View dashboard at: file://$LOG_DIR/api-monitoring-dashboard.html"
echo "📝 View logs: tail -f $LOG_DIR/api-monitoring.log"