#!/bin/bash

# API Response Time Monitoring Script
# Purpose: 모든 주요 API 엔드포인트의 응답시간을 측정하고 임계값 기반 알람 제공
# Author: Blacklist Management System
# Version: 1.0.0
# Created: 2025-08-22

set -euo pipefail

# === Configuration ===
readonly SCRIPT_NAME=$(basename "$0")
readonly SCRIPT_DIR=$(dirname "$0")
readonly BASE_URL="${API_MONITOR_BASE_URL:-http://localhost:32542}"
readonly LOG_DIR="${API_MONITOR_LOG_DIR:-/var/log}"
readonly LOG_FILE="${LOG_DIR}/api-monitoring.log"
readonly JSON_LOG_FILE="${LOG_DIR}/api-monitoring.json"
readonly TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
readonly ISO_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Performance Thresholds (milliseconds)
readonly THRESHOLD_EXCELLENT=50
readonly THRESHOLD_GOOD=200
readonly THRESHOLD_ACCEPTABLE=1000
readonly THRESHOLD_POOR=5000

# Colors for output
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# === API Endpoints Configuration ===
declare -A ENDPOINTS=(
    # Health & Status (Core endpoints - always available)
    ["/health"]="Health Check"
    ["/healthz"]="K8s Health Check" 
    ["/ready"]="K8s Readiness Check"
    ["/api/health"]="Detailed Health Check"
    ["/"]="Root Service Info"
    
    # Core API (Basic functionality)
    ["/api/blacklist/active"]="Active Blacklist IPs"
    
    # Additional endpoints (may return 404 in minimal mode)
    ["/api/fortigate"]="FortiGate External Connector"
    ["/api/collection/status"]="Collection Status"
    ["/api/v2/analytics/summary"]="Analytics Summary"
    ["/api/v2/sources/status"]="Sources Status"
)

# === Functions ===

log_message() {
    local level="$1"
    shift
    local message="$*"
    echo "[$TIMESTAMP] [$level] $message" | tee -a "$LOG_FILE"
}

log_json() {
    local endpoint="$1"
    local response_time="$2"
    local status_code="$3"
    local status_level="$4"
    local description="$5"
    
    local json_entry=$(cat <<EOF
{
  "timestamp": "$ISO_TIMESTAMP",
  "endpoint": "$endpoint",
  "response_time_ms": $response_time,
  "status_code": $status_code,
  "status_level": "$status_level",
  "description": "$description",
  "base_url": "$BASE_URL"
}
EOF
)
    echo "$json_entry" >> "$JSON_LOG_FILE"
}

get_status_level() {
    local response_time="$1"
    local status_code="$2"
    
    # Check if request failed
    if [[ "$status_code" -eq 0 ]] || [[ "$status_code" -ge 500 ]]; then
        echo "CRITICAL"
        return
    fi
    
    if [[ "$status_code" -ge 400 ]]; then
        echo "WARNING"
        return
    fi
    
    # Check response time thresholds
    if [[ "$response_time" -le "$THRESHOLD_EXCELLENT" ]]; then
        echo "EXCELLENT"
    elif [[ "$response_time" -le "$THRESHOLD_GOOD" ]]; then
        echo "GOOD"
    elif [[ "$response_time" -le "$THRESHOLD_ACCEPTABLE" ]]; then
        echo "ACCEPTABLE"
    elif [[ "$response_time" -le "$THRESHOLD_POOR" ]]; then
        echo "POOR"
    else
        echo "CRITICAL"
    fi
}

get_color_for_level() {
    local level="$1"
    case "$level" in
        "EXCELLENT") echo "$GREEN" ;;
        "GOOD") echo "$GREEN" ;;
        "ACCEPTABLE") echo "$YELLOW" ;;
        "POOR") echo "$YELLOW" ;;
        "WARNING") echo "$YELLOW" ;;
        "CRITICAL") echo "$RED" ;;
        *) echo "$NC" ;;
    esac
}

measure_endpoint() {
    local endpoint="$1"
    local description="$2"
    local url="${BASE_URL}${endpoint}"
    
    echo -n "Testing $endpoint... "
    
    # Measure response time and get status code
    local response
    response=$(curl -o /dev/null -s -w "%{time_total}:%{http_code}" \
                  --max-time 30 \
                  --connect-timeout 10 \
                  "$url" 2>/dev/null || echo "0:0")
    
    local time_total=$(echo "$response" | cut -d: -f1)
    local status_code=$(echo "$response" | cut -d: -f2)
    
    # Convert to milliseconds (handle empty response)
    local response_time_ms
    if [[ -n "$time_total" && "$time_total" != "0" ]]; then
        response_time_ms=$(printf "%.0f" $(echo "$time_total * 1000" | bc))
    else
        response_time_ms=0
    fi
    
    # Get status level
    local status_level
    status_level=$(get_status_level "$response_time_ms" "$status_code")
    
    # Get color for output
    local color
    color=$(get_color_for_level "$status_level")
    
    # Output results
    printf "${color}%s${NC} (%dms, HTTP %s)\n" "$status_level" "$response_time_ms" "$status_code"
    
    # Log to files
    log_message "INFO" "Endpoint: $endpoint | Response: ${response_time_ms}ms | Status: $status_code | Level: $status_level"
    log_json "$endpoint" "$response_time_ms" "$status_code" "$status_level" "$description"
    
    # Check for alerts
    if [[ "$status_level" == "CRITICAL" ]] || [[ "$status_level" == "POOR" ]]; then
        log_message "ALERT" "THRESHOLD EXCEEDED: $endpoint responded in ${response_time_ms}ms (Status: $status_code) - Level: $status_level"
    fi
    
    return 0
}

create_monitoring_dashboard() {
    local dashboard_file="${LOG_DIR}/api-monitoring-dashboard.html"
    
    cat > "$dashboard_file" <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>API Response Time Monitoring</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .endpoint-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-excellent { border-left: 5px solid #28a745; }
        .status-good { border-left: 5px solid #28a745; }
        .status-acceptable { border-left: 5px solid #ffc107; }
        .status-poor { border-left: 5px solid #fd7e14; }
        .status-critical { border-left: 5px solid #dc3545; }
        .status-warning { border-left: 5px solid #ffc107; }
        .timestamp { color: #666; font-size: 0.9em; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .metrics { display: flex; justify-content: space-around; margin: 20px 0; }
        .metric { text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .metric-label { color: #666; }
    </style>
    <script>
        function refreshPage() {
            location.reload();
        }
        
        // Auto-refresh every 5 minutes
        setTimeout(refreshPage, 300000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 API Response Time Monitoring</h1>
            <p>Real-time performance metrics for Blacklist Management System</p>
            <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh</button>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value" id="total-endpoints">-</div>
                <div class="metric-label">Total Endpoints</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="avg-response">-</div>
                <div class="metric-label">Avg Response (ms)</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="alerts-count">-</div>
                <div class="metric-label">Alerts</div>
            </div>
        </div>
        
        <div class="status-grid" id="endpoints-grid">
            <p>Loading monitoring data...</p>
        </div>
        
        <div class="timestamp">
            Last updated: <span id="last-updated">-</span> | 
            Thresholds: Excellent ≤50ms | Good ≤200ms | Acceptable ≤1000ms | Poor ≤5000ms
        </div>
    </div>
    
    <script>
        // This would be populated with real-time data in a production setup
        document.getElementById('last-updated').textContent = new Date().toLocaleString();
        document.getElementById('total-endpoints').textContent = Object.keys(ENDPOINTS || {}).length || '-';
    </script>
</body>
</html>
EOF

    log_message "INFO" "Created monitoring dashboard: $dashboard_file"
}

setup_cron_job() {
    local cron_entry="*/5 * * * * /usr/local/bin/api-monitor.sh > /dev/null 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "api-monitor.sh"; then
        log_message "INFO" "Cron job already exists"
        return 0
    fi
    
    # Add cron job
    (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
    log_message "INFO" "Added cron job: $cron_entry"
}

show_summary() {
    local total_endpoints=${#ENDPOINTS[@]}
    local excellent_count=0
    local good_count=0
    local acceptable_count=0
    local poor_count=0
    local critical_count=0
    local warning_count=0
    local total_response_time=0
    
    # Count results from last run (this is simplified - in real implementation would parse JSON log)
    echo
    echo "=== Monitoring Summary ==="
    echo "Timestamp: $TIMESTAMP"
    echo "Base URL: $BASE_URL"
    echo "Total Endpoints: $total_endpoints"
    echo "Log Files:"
    echo "  - General: $LOG_FILE"
    echo "  - JSON: $JSON_LOG_FILE"
    echo "  - Dashboard: ${LOG_DIR}/api-monitoring-dashboard.html"
    echo
    echo "Performance Thresholds:"
    echo "  🟢 Excellent: ≤ ${THRESHOLD_EXCELLENT}ms"
    echo "  🟢 Good: ≤ ${THRESHOLD_GOOD}ms"
    echo "  🟡 Acceptable: ≤ ${THRESHOLD_ACCEPTABLE}ms"
    echo "  🟡 Poor: ≤ ${THRESHOLD_POOR}ms"
    echo "  🔴 Critical: > ${THRESHOLD_POOR}ms or failed requests"
    echo
}

# === Main Execution ===

main() {
    local command="${1:-monitor}"
    
    case "$command" in
        "monitor")
            log_message "INFO" "Starting API monitoring for $BASE_URL"
            
            # Ensure log directory exists
            mkdir -p "$LOG_DIR"
            
            # Initialize JSON log if needed
            if [[ ! -f "$JSON_LOG_FILE" ]]; then
                echo "[]" > "$JSON_LOG_FILE"
            fi
            
            echo "🚀 API Response Time Monitoring"
            echo "Base URL: $BASE_URL"
            echo "Timestamp: $TIMESTAMP"
            echo
            
            # Test all endpoints
            for endpoint in "${!ENDPOINTS[@]}"; do
                measure_endpoint "$endpoint" "${ENDPOINTS[$endpoint]}"
            done
            
            show_summary
            create_monitoring_dashboard
            ;;
            
        "setup")
            log_message "INFO" "Setting up API monitoring system"
            setup_cron_job
            create_monitoring_dashboard
            echo "✅ API monitoring system setup complete"
            echo "   - Cron job scheduled every 5 minutes"
            echo "   - Logs: $LOG_FILE"
            echo "   - JSON data: $JSON_LOG_FILE"
            echo "   - Dashboard: ${LOG_DIR}/api-monitoring-dashboard.html"
            ;;
            
        "test")
            log_message "INFO" "Testing API monitoring (single run)"
            main "monitor"
            ;;
            
        "help"|"-h"|"--help")
            cat <<EOF
API Response Time Monitoring Script

Usage: $SCRIPT_NAME [command]

Commands:
  monitor    Run monitoring once (default)
  setup      Setup cron job and dashboard
  test       Same as monitor (for testing)
  help       Show this help message

Environment Variables:
  API_MONITOR_BASE_URL    Base URL for API (default: http://localhost:32542)
  API_MONITOR_LOG_DIR     Log directory (default: /var/log)

Examples:
  $SCRIPT_NAME                    # Run monitoring once
  $SCRIPT_NAME setup              # Setup automated monitoring
  API_MONITOR_BASE_URL=https://blacklist.jclee.me $SCRIPT_NAME monitor
EOF
            ;;
            
        *)
            echo "Error: Unknown command '$command'"
            echo "Use '$SCRIPT_NAME help' for usage information"
            exit 1
            ;;
    esac
}

# Check dependencies
if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required but not installed"
    exit 1
fi

if ! command -v bc >/dev/null 2>&1; then
    echo "Error: bc is required but not installed"
    exit 1
fi

# Run main function
main "$@"