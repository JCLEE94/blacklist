#!/bin/bash

# Production Log Analysis Script
# Usage: ./analyze_production_logs.sh

SERVER="docker@192.168.50.215"
PORT="1111"
PASSWORD="bingogo1"

echo "================================"
echo "🔍 Production Log Analysis"
echo "================================"
echo ""

# Function to execute remote command
remote_exec() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER -p $PORT "$1"
}

# 1. Container Status Analysis
echo "📊 Container Status Analysis"
echo "----------------------------"
remote_exec "/usr/local/bin/docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" | column -t

echo ""
echo "🔴 Stopped Containers:"
remote_exec "/usr/local/bin/docker ps -a --filter 'status=exited' --format '{{.Names}} (Exit: {{.ExitCode}})'"

# 2. Error Analysis
echo ""
echo "❌ Recent Errors (Last 24h)"
echo "----------------------------"

# Check each container for errors
for container in blacklist safework-backend safework-frontend; do
    echo ""
    echo "Container: $container"
    echo "..................."
    remote_exec "/usr/local/bin/docker logs $container --since 24h 2>&1 | grep -i 'error\|exception\|failed' | tail -5" || echo "No recent errors"
done

# 3. Resource Usage
echo ""
echo "💾 Resource Usage"
echo "-----------------"
remote_exec "/usr/local/bin/docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'"

# 4. Health Check Status
echo ""
echo "🏥 Health Check Status"
echo "----------------------"
remote_exec "/usr/local/bin/docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'healthy|unhealthy'"

# 5. Disk Usage
echo ""
echo "💽 Disk Usage"
echo "-------------"
remote_exec "df -h | grep -E '^/dev/|Filesystem'"

# 6. Generate Report
echo ""
echo "📝 Analysis Summary"
echo "==================="

TOTAL=$(remote_exec "/usr/local/bin/docker ps -a -q | wc -l")
RUNNING=$(remote_exec "/usr/local/bin/docker ps -q | wc -l")
STOPPED=$((TOTAL - RUNNING))

echo "Total Containers: $TOTAL"
echo "Running: $RUNNING"
echo "Stopped: $STOPPED"

if [ $STOPPED -gt 0 ]; then
    echo ""
    echo "⚠️  WARNING: $STOPPED containers are stopped!"
    echo "Affected services:"
    remote_exec "/usr/local/bin/docker ps -a --filter 'status=exited' --format '- {{.Names}}'"
fi

echo ""
echo "Report generated at: $(date)"
echo "================================"