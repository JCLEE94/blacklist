#!/bin/bash

# Real-time Production Monitoring
# Usage: ./monitor_production.sh [container_name]

SERVER="docker@192.168.50.215"
PORT="1111"
PASSWORD="bingogo1"
CONTAINER=${1:-"blacklist"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Real-time Production Monitoring${NC}"
echo -e "${GREEN}Container: $CONTAINER${NC}"
echo "================================"

# Function to execute remote command
remote_exec() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER -p $PORT "$1"
}

# Check if container exists
EXISTS=$(remote_exec "/usr/local/bin/docker ps -a --filter name=$CONTAINER --format '{{.Names}}'")
if [ -z "$EXISTS" ]; then
    echo -e "${RED}❌ Container '$CONTAINER' not found!${NC}"
    echo "Available containers:"
    remote_exec "/usr/local/bin/docker ps -a --format '{{.Names}}'"
    exit 1
fi

# Monitor loop
while true; do
    clear
    echo -e "${GREEN}📊 Production Monitor - $(date)${NC}"
    echo "================================"
    
    # Container Status
    STATUS=$(remote_exec "/usr/local/bin/docker ps -a --filter name=$CONTAINER --format '{{.Status}}'")
    if [[ $STATUS == *"Up"* ]]; then
        echo -e "Status: ${GREEN}$STATUS${NC}"
    else
        echo -e "Status: ${RED}$STATUS${NC}"
    fi
    
    # CPU and Memory
    echo ""
    echo "Resource Usage:"
    remote_exec "/usr/local/bin/docker stats --no-stream --format 'CPU: {{.CPUPerc}} | Memory: {{.MemUsage}}' $CONTAINER"
    
    # Recent Logs
    echo ""
    echo "Recent Logs (Last 20 lines):"
    echo "----------------------------"
    remote_exec "/usr/local/bin/docker logs $CONTAINER --tail 20 2>&1"
    
    # Error Count
    echo ""
    ERROR_COUNT=$(remote_exec "/usr/local/bin/docker logs $CONTAINER --since 1h 2>&1 | grep -c -i 'error\|exception' || echo 0")
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${RED}⚠️  Errors in last hour: $ERROR_COUNT${NC}"
    else
        echo -e "${GREEN}✅ No errors in last hour${NC}"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit | Refreshing in 30 seconds..."
    sleep 30
done