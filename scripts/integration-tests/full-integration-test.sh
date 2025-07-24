#!/bin/bash

# Full Integration Test Suite
# Comprehensive testing of all deployment components

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${BASE_URL:-http://192.168.50.110:32542}"
EXTERNAL_URL="${EXTERNAL_URL:-https://blacklist.jclee.me}"
NAMESPACE="${APP_NAMESPACE:-blacklist}"
APP_NAME="${APP_NAME:-blacklist}"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_LOG="/tmp/integration-test-$(date +%Y%m%d-%H%M%S).log"

echo "===================================="
echo "Full Integration Test Suite"
echo "===================================="
echo "Base URL: $BASE_URL"
echo "External URL: $EXTERNAL_URL"
echo "Log file: $TEST_LOG"
echo ""

# Function to log output
log() {
    echo "$1" | tee -a "$TEST_LOG"
}

# Function to run API test
test_api() {
    local test_name=$1
    local endpoint=$2
    local expected_status=${3:-200}
    local check_content=$4
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing API: $test_name... "
    
    # Make request and capture response
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    # Log full response
    {
        echo "=== Test: $test_name ==="
        echo "Endpoint: $endpoint"
        echo "Expected Status: $expected_status"
        echo "Actual Status: $HTTP_CODE"
        echo "Response Body: $BODY"
        echo ""
    } >> "$TEST_LOG"
    
    # Check status code
    if [ "$HTTP_CODE" != "$expected_status" ]; then
        echo -e "${RED}FAILED${NC} (HTTP $HTTP_CODE)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
    
    # Check content if specified
    if [ -n "$check_content" ]; then
        if echo "$BODY" | grep -q "$check_content"; then
            echo -e "${GREEN}PASSED${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "${RED}FAILED${NC} (content check)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        echo -e "${GREEN}PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    fi
}

# Function to test functionality
test_function() {
    local test_name=$1
    local test_command=$2
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing Function: $test_name... "
    
    {
        echo "=== Test: $test_name ==="
        echo "Command: $test_command"
    } >> "$TEST_LOG"
    
    if eval "$test_command" >> "$TEST_LOG" 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 1. Health and Basic Endpoints
log ""
log "${BLUE}1. Health and Basic Endpoints${NC}"
log "-----------------------------"

test_api "Health Check" "/health" 200 "healthy"
test_api "Root Page" "/" 200 "Blacklist Management"
test_api "Test Endpoint" "/test" 200 "Test response"

# 2. Collection Management
log ""
log "${BLUE}2. Collection Management${NC}"
log "------------------------"

test_api "Collection Status" "/api/collection/status" 200 "collection_enabled"
test_api "Enable Collection" "/api/collection/enable" 200 "" "POST"
test_api "Disable Collection" "/api/collection/disable" 200 "" "POST"

# 3. Data Retrieval
log ""
log "${BLUE}3. Data Retrieval${NC}"
log "-----------------"

test_api "Active Blacklist" "/api/blacklist/active" 200
test_api "FortiGate Format" "/api/fortigate" 200 "feed_name"
test_api "Statistics" "/api/stats" 200 "total_ips"
test_api "Detection Trends" "/api/stats/detection-trends" 200

# 4. V2 API Endpoints
log ""
log "${BLUE}4. V2 API Endpoints${NC}"
log "-------------------"

test_api "Enhanced Blacklist" "/api/v2/blacklist/enhanced" 200 "ips"
test_api "Analytics Trends" "/api/v2/analytics/trends" 200 "trend_data"
test_api "Sources Status" "/api/v2/sources/status" 200 "sources"

# 5. Search Functionality
log ""
log "${BLUE}5. Search Functionality${NC}"
log "-----------------------"

test_api "Search Invalid IP" "/api/search/1.1.1.1" 200 "not_found"
test_api "Batch Search" "/api/search" 200 "results" "POST"

# 6. Docker Integration
log ""
log "${BLUE}6. Docker Integration${NC}"
log "---------------------"

test_api "Docker Containers" "/api/docker/containers" 200
test_api "Docker Logs UI" "/docker-logs" 200 "Docker Logs"

# 7. Kubernetes Integration
log ""
log "${BLUE}7. Kubernetes Integration${NC}"
log "-------------------------"

test_function "Pods Running" "kubectl get pods -n $NAMESPACE -l app=$APP_NAME | grep -q Running"
test_function "Service Exists" "kubectl get svc $APP_NAME -n $NAMESPACE"
test_function "No Restart Loops" "[ $(kubectl get pods -n $NAMESPACE -l app=$APP_NAME -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}') -lt 3 ]"

# 8. ArgoCD Status
log ""
log "${BLUE}8. ArgoCD Status${NC}"
log "----------------"

if command -v argocd &> /dev/null; then
    test_function "ArgoCD App Synced" "argocd app get $APP_NAME --grpc-web | grep -q 'Sync Status:.*Synced'"
    test_function "ArgoCD App Healthy" "argocd app get $APP_NAME --grpc-web | grep -q 'Health Status:.*Healthy'"
else
    log "${YELLOW}ArgoCD CLI not available, skipping ArgoCD tests${NC}"
fi

# 9. Performance Tests
log ""
log "${BLUE}9. Performance Tests${NC}"
log "--------------------"

# Test response time
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "Testing Performance: Response Time... "
START_TIME=$(date +%s%N)
curl -s -o /dev/null "$BASE_URL/health"
END_TIME=$(date +%s%N)
RESPONSE_TIME=$((($END_TIME - $START_TIME) / 1000000))

if [ $RESPONSE_TIME -lt 100 ]; then
    echo -e "${GREEN}PASSED${NC} (${RESPONSE_TIME}ms)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}WARNING${NC} (${RESPONSE_TIME}ms > 100ms)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test concurrent requests
test_function "Concurrent Requests" "seq 1 10 | xargs -P10 -I{} curl -s -o /dev/null -w '%{http_code}\n' $BASE_URL/health | grep -q 200"

# 10. Data Integrity
log ""
log "${BLUE}10. Data Integrity${NC}"
log "------------------"

# Test data persistence
test_function "Database Accessible" "curl -s $BASE_URL/api/stats | jq -r '.total_ips' | grep -E '^[0-9]+$'"

# Test collection functionality (warning only)
echo -n "Testing Function: REGTECH Collection... "
if curl -X POST -s "$BASE_URL/api/collection/regtech/trigger" | grep -q "error"; then
    echo -e "${YELLOW}WARNING${NC} (Expected - External auth required)"
else
    echo -e "${GREEN}PASSED${NC}"
fi

# 11. External Access (Optional)
log ""
log "${BLUE}11. External Access Tests${NC}"
log "-------------------------"

if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$EXTERNAL_URL" | grep -q "200\|502"; then
    test_api "External Health" "$EXTERNAL_URL/health" 200 "healthy"
else
    log "${YELLOW}External URL not accessible, skipping external tests${NC}"
fi

# 12. Security Tests
log ""
log "${BLUE}12. Security Tests${NC}"
log "------------------"

test_api "Invalid Endpoint" "/api/invalid/endpoint" 404
test_api "SQL Injection Test" "/api/search/1'%20OR%20'1'='1" 200 "not_found"

# Summary Report
log ""
log "===================================="
log "${BLUE}Integration Test Summary${NC}"
log "===================================="
log "Total Tests: $TOTAL_TESTS"
log "Passed: ${GREEN}$PASSED_TESTS${NC}"
log "Failed: ${RED}$FAILED_TESTS${NC}"
log "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
log ""

# Generate detailed report
{
    echo ""
    echo "=== Detailed Test Report ==="
    echo "Generated: $(date)"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo ""
    
    # System information
    echo "=== System Information ==="
    kubectl get nodes | head -5
    echo ""
    kubectl get pods -n $NAMESPACE
    echo ""
    
    # Application logs (last 20 lines)
    echo "=== Recent Application Logs ==="
    kubectl logs -n $NAMESPACE deployment/$APP_NAME --tail=20 2>/dev/null || echo "Could not fetch logs"
    
} >> "$TEST_LOG"

if [ $FAILED_TESTS -eq 0 ]; then
    log "${GREEN}✅ All integration tests passed!${NC}"
    log ""
    log "The deployment is working correctly."
    log "Full test log: $TEST_LOG"
    exit 0
else
    log "${RED}❌ Some integration tests failed.${NC}"
    log ""
    log "Please review the failures and check:"
    log "- Application logs: kubectl logs -f deployment/$APP_NAME -n $NAMESPACE"
    log "- Pod status: kubectl get pods -n $NAMESPACE"
    log "- Full test log: $TEST_LOG"
    exit 1
fi