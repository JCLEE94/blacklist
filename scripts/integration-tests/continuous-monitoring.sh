#!/bin/bash

# Continuous Monitoring Script
# Monitors deployment health and alerts on issues

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://192.168.50.110:32542}"
NAMESPACE="${APP_NAMESPACE:-blacklist}"
APP_NAME="${APP_NAME:-blacklist}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"  # seconds
ALERT_THRESHOLD="${ALERT_THRESHOLD:-3}" # failures before alert

# State tracking
FAILURE_COUNT=0
LAST_STATUS="UNKNOWN"
START_TIME=$(date +%s)

echo "===================================="
echo "Continuous Deployment Monitoring"
echo "===================================="
echo "URL: $BASE_URL"
echo "Check Interval: ${CHECK_INTERVAL}s"
echo "Alert Threshold: $ALERT_THRESHOLD failures"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Function to check health
check_health() {
    local status="HEALTHY"
    local details=""
    
    # Check health endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BASE_URL/health" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" != "200" ]; then
        status="UNHEALTHY"
        details="Health check failed (HTTP $HTTP_CODE)"
    fi
    
    # Check pod status
    if [ "$status" == "HEALTHY" ]; then
        RUNNING_PODS=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | grep -c Running || echo 0)
        TOTAL_PODS=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | wc -l || echo 0)
        
        if [ "$RUNNING_PODS" -eq 0 ] || [ "$RUNNING_PODS" -lt "$TOTAL_PODS" ]; then
            status="DEGRADED"
            details="Only $RUNNING_PODS/$TOTAL_PODS pods running"
        fi
    fi
    
    # Check for restart loops
    if [ "$status" == "HEALTHY" ]; then
        MAX_RESTARTS=$(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}' 2>/dev/null | tr ' ' '\n' | sort -nr | head -1 || echo 0)
        
        if [ "$MAX_RESTARTS" -gt 5 ]; then
            status="WARNING"
            details="High restart count: $MAX_RESTARTS"
        fi
    fi
    
    echo "$status|$details"
}

# Function to send alert
send_alert() {
    local message=$1
    local severity=$2
    
    echo ""
    echo -e "${RED}🚨 ALERT [$severity]: $message${NC}"
    echo ""
    
    # Log to file
    echo "[$(date)] ALERT [$severity]: $message" >> /tmp/blacklist-monitoring.log
    
    # Here you could add:
    # - Send email notification
    # - Post to Slack/Discord
    # - Trigger PagerDuty
    # - Create GitHub issue
}

# Function to get metrics
get_metrics() {
    # Response time
    START=$(date +%s%N)
    curl -s -o /dev/null "$BASE_URL/health" 2>/dev/null
    END=$(date +%s%N)
    RESPONSE_TIME=$((($END - $START) / 1000000))
    
    # Memory usage
    MEMORY=$(kubectl top pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | awk '{sum+=$3} END {print sum}' || echo "N/A")
    
    # CPU usage
    CPU=$(kubectl top pods -n $NAMESPACE -l app=$APP_NAME --no-headers 2>/dev/null | awk '{sum+=$2} END {print sum}' || echo "N/A")
    
    echo "Response: ${RESPONSE_TIME}ms | Memory: ${MEMORY}Mi | CPU: ${CPU}m"
}

# Function to display status
display_status() {
    local status=$1
    local details=$2
    local metrics=$3
    local uptime=$(($(date +%s) - START_TIME))
    
    # Clear line and print status
    printf "\r%-80s" " "  # Clear line
    
    case $status in
        "HEALTHY")
            printf "\r[%s] ${GREEN}● HEALTHY${NC} | %s | Uptime: %ds" "$(date +%H:%M:%S)" "$metrics" "$uptime"
            ;;
        "DEGRADED")
            printf "\r[%s] ${YELLOW}● DEGRADED${NC} | %s | %s" "$(date +%H:%M:%S)" "$details" "$metrics"
            ;;
        "WARNING")
            printf "\r[%s] ${YELLOW}⚠ WARNING${NC} | %s | %s" "$(date +%H:%M:%S)" "$details" "$metrics"
            ;;
        "UNHEALTHY")
            printf "\r[%s] ${RED}● UNHEALTHY${NC} | %s" "$(date +%H:%M:%S)" "$details"
            ;;
    esac
}

# Main monitoring loop
while true; do
    # Check health
    RESULT=$(check_health)
    STATUS=$(echo $RESULT | cut -d'|' -f1)
    DETAILS=$(echo $RESULT | cut -d'|' -f2)
    
    # Get metrics if healthy
    METRICS=""
    if [ "$STATUS" != "UNHEALTHY" ]; then
        METRICS=$(get_metrics)
    fi
    
    # Display current status
    display_status "$STATUS" "$DETAILS" "$METRICS"
    
    # Handle state changes
    if [ "$STATUS" != "$LAST_STATUS" ]; then
        echo ""  # New line for state change
        
        case $STATUS in
            "HEALTHY")
                if [ "$LAST_STATUS" != "UNKNOWN" ]; then
                    echo -e "${GREEN}✅ System recovered${NC}"
                    send_alert "System recovered from $LAST_STATUS state" "INFO"
                fi
                FAILURE_COUNT=0
                ;;
            "DEGRADED"|"WARNING")
                send_alert "$DETAILS" "WARNING"
                ;;
            "UNHEALTHY")
                FAILURE_COUNT=$((FAILURE_COUNT + 1))
                if [ $FAILURE_COUNT -ge $ALERT_THRESHOLD ]; then
                    send_alert "System unhealthy for $FAILURE_COUNT checks: $DETAILS" "CRITICAL"
                    
                    # Collect diagnostic information
                    echo ""
                    echo "Collecting diagnostics..."
                    {
                        echo "=== Diagnostic Report $(date) ==="
                        echo "Status: $STATUS"
                        echo "Details: $DETAILS"
                        echo ""
                        echo "=== Pod Status ==="
                        kubectl get pods -n $NAMESPACE -l app=$APP_NAME
                        echo ""
                        echo "=== Recent Events ==="
                        kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10
                        echo ""
                        echo "=== Application Logs ==="
                        kubectl logs -n $NAMESPACE deployment/$APP_NAME --tail=50
                    } > /tmp/blacklist-diagnostics-$(date +%Y%m%d-%H%M%S).log
                    
                    echo "Diagnostics saved to /tmp/blacklist-diagnostics-*.log"
                fi
                ;;
        esac
        
        LAST_STATUS=$STATUS
    fi
    
    # Sleep before next check
    sleep $CHECK_INTERVAL
done