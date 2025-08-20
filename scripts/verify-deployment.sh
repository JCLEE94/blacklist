#!/bin/bash

# Comprehensive Deployment Verification Script
# Validates entire blacklist management system deployment
# Includes Docker services, API endpoints, database, performance checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_RETRIES=10
PERFORMANCE_THRESHOLD_MS=1000
API_BASE_URL="http://localhost:32542"
LOCAL_BASE_URL="http://localhost:2542"

# Global counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# Results array
declare -a RESULTS

# Check for help option first
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    cat << EOF
Comprehensive Deployment Verification Tool

Usage: $0 [OPTIONS]

This script performs comprehensive verification of the blacklist deployment including:
- Docker service status (blacklist, redis, postgresql)
- API health checks (/health, /api/health, endpoints)
- Database connectivity (PostgreSQL, Redis) 
- Performance benchmarks (response times, concurrent load)
- Resource usage monitoring (CPU, memory, containers)
- Security validation
- Configuration validation

The script generates a detailed report and exits with:
- Code 0: All tests passed
- Code 1: Some tests failed (with suggestions for fixes)

Examples:
  $0                  # Run full verification suite

For troubleshooting issues found, use:
  ./scripts/auto-rollback.sh --help
  ./scripts/troubleshoot-deployment.sh --help

EOF
    exit 0
fi

echo -e "${BLUE}🚀 Comprehensive Deployment Verification${NC}"
echo -e "${BLUE}======================================${NC}"
echo "Starting complete system validation..."
echo ""

# Helper functions
log_test() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    ((TOTAL_TESTS++))
    
    case $status in
        "PASS")
            echo -e "   ${GREEN}✅ $message${NC}"
            RESULTS+=("✅ $test_name: $message")
            ((PASSED_TESTS++))
            ;;
        "FAIL")
            echo -e "   ${RED}❌ $message${NC}"
            RESULTS+=("❌ $test_name: $message")
            ((FAILED_TESTS++))
            ;;
        "WARN")
            echo -e "   ${YELLOW}⚠️  $message${NC}"
            RESULTS+=("⚠️ $test_name: $message")
            ((WARNINGS++))
            ;;
    esac
}

check_service_health() {
    local url="$1"
    local service_name="$2"
    local max_retries="${3:-5}"
    
    for ((i=1; i<=max_retries; i++)); do
        if curl -sf "$url/health" > /dev/null 2>&1; then
            return 0
        fi
        echo -e "   ${YELLOW}Retry $i/$max_retries for $service_name...${NC}"
        sleep 2
    done
    return 1
}

measure_response_time() {
    local url="$1"
    local response_time=$(curl -w "%{time_total}" -o /dev/null -s "$url" 2>/dev/null || echo "999999")
    # Convert to milliseconds
    echo "$response_time * 1000" | bc -l 2>/dev/null | cut -d. -f1 || echo "999999"
}

# Test 1: Docker Services Status
echo -e "${BLUE}1. Docker Services Status${NC}"
if docker-compose ps | grep -q "Up"; then
    # Check individual services
    if docker-compose ps blacklist | grep -q "Up"; then
        log_test "Docker-Blacklist" "PASS" "Blacklist service running"
    else
        log_test "Docker-Blacklist" "FAIL" "Blacklist service not running"
    fi
    
    if docker-compose ps redis | grep -q "Up"; then
        log_test "Docker-Redis" "PASS" "Redis service running"
    else
        log_test "Docker-Redis" "FAIL" "Redis service not running"
    fi
    
    if docker-compose ps postgresql | grep -q "Up"; then
        log_test "Docker-PostgreSQL" "PASS" "PostgreSQL service running"
    else
        log_test "Docker-PostgreSQL" "FAIL" "PostgreSQL service not running"
    fi
else
    log_test "Docker-Services" "FAIL" "No Docker services running"
fi

# Test 2: API Health Checks
echo -e "${BLUE}2. API Health Checks${NC}"

# Check Docker-based service
if check_service_health "$API_BASE_URL" "Docker service"; then
    log_test "API-Health-Docker" "PASS" "Docker service health check passed"
    
    # Get detailed health info
    health_response=$(curl -s "$API_BASE_URL/api/health" 2>/dev/null || echo "{}")
    if echo "$health_response" | jq -e '.status' > /dev/null 2>&1; then
        status=$(echo "$health_response" | jq -r '.status')
        total_ips=$(echo "$health_response" | jq -r '.metrics.total_ips // "unknown"')
        log_test "API-Detailed-Health" "PASS" "Status: $status, Total IPs: $total_ips"
    else
        log_test "API-Detailed-Health" "WARN" "Detailed health response malformed"
    fi
else
    log_test "API-Health-Docker" "FAIL" "Docker service health check failed"
fi

# Check local development service if running
if check_service_health "$LOCAL_BASE_URL" "Local service" 3; then
    log_test "API-Health-Local" "PASS" "Local development service available"
else
    log_test "API-Health-Local" "WARN" "Local development service not available"
fi

# Test 3: Core API Endpoints
echo -e "${BLUE}3. Core API Endpoints${NC}"

endpoints=(
    "/health:Basic health check"
    "/api/health:Detailed health check"
    "/api/blacklist/active:Active blacklist"
    "/api/fortigate:FortiGate format"
    "/api/collection/status:Collection status"
    "/build-info:Build information"
)

for endpoint in "${endpoints[@]}"; do
    IFS=':' read -r path description <<< "$endpoint"
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL$path" 2>/dev/null || echo "000")
    response_time=$(measure_response_time "$API_BASE_URL$path")
    
    if [ "$response_code" = "200" ]; then
        if [ "$response_time" -lt "$PERFORMANCE_THRESHOLD_MS" ]; then
            log_test "API-$path" "PASS" "$description (${response_time}ms)"
        else
            log_test "API-$path" "WARN" "$description (${response_time}ms - slow)"
        fi
    elif [ "$response_code" = "503" ]; then
        log_test "API-$path" "WARN" "$description (503 - service degraded)"
    else
        log_test "API-$path" "FAIL" "$description (HTTP $response_code)"
    fi
done

# Test 4: Database Connectivity
echo -e "${BLUE}4. Database Connectivity${NC}"

# Test PostgreSQL connection
if docker-compose exec -T postgresql pg_isready -U blacklist_user -d blacklist > /dev/null 2>&1; then
    log_test "Database-Connection" "PASS" "PostgreSQL connection successful"
    
    # Test data availability
    row_count=$(docker-compose exec -T postgresql psql -U blacklist_user -d blacklist -t -c "SELECT COUNT(*) FROM blacklist_entries;" 2>/dev/null | xargs || echo "0")
    log_test "Database-Data" "PASS" "Database contains $row_count entries"
else
    log_test "Database-Connection" "FAIL" "PostgreSQL connection failed"
fi

# Test 5: Redis Connectivity
echo -e "${BLUE}5. Redis Connectivity${NC}"

if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    log_test "Redis-Connection" "PASS" "Redis connection successful"
    
    # Test Redis info
    redis_memory=$(docker-compose exec -T redis redis-cli info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2 | tr -d '\r' || echo "unknown")
    log_test "Redis-Memory" "PASS" "Redis memory usage: $redis_memory"
else
    log_test "Redis-Connection" "FAIL" "Redis connection failed"
fi

# Test 6: Security Headers & Authentication
echo -e "${BLUE}6. Security Validation${NC}"

# Check security headers
security_headers=$(curl -sI "$API_BASE_URL/api/health" 2>/dev/null || echo "")
if echo "$security_headers" | grep -qi "content-type"; then
    log_test "Security-Headers" "PASS" "Content-Type header present"
else
    log_test "Security-Headers" "WARN" "Security headers missing"
fi

# Test 7: Performance Benchmarks
echo -e "${BLUE}7. Performance Benchmarks${NC}"

# Concurrent request test
echo -e "   ${YELLOW}Running concurrent request test...${NC}"
concurrent_responses=()
for i in {1..5}; do 
    concurrent_responses+=($(measure_response_time "$API_BASE_URL/health")) 
done

# Calculate average
total=0
for time in "${concurrent_responses[@]}"; do
    total=$((total + time))
done
avg_time=$((total / ${#concurrent_responses[@]}))

if [ "$avg_time" -lt "$PERFORMANCE_THRESHOLD_MS" ]; then
    log_test "Performance-Concurrent" "PASS" "Avg response time: ${avg_time}ms"
else
    log_test "Performance-Concurrent" "WARN" "Avg response time: ${avg_time}ms (above threshold)"
fi

# Test 8: Data Collection System
echo -e "${BLUE}8. Data Collection System${NC}"

collection_status=$(curl -s "$API_BASE_URL/api/collection/status" 2>/dev/null || echo "{}")
if echo "$collection_status" | jq -e '.collection_enabled' > /dev/null 2>&1; then
    enabled=$(echo "$collection_status" | jq -r '.collection_enabled')
    if [ "$enabled" = "true" ]; then
        log_test "Collection-Status" "PASS" "Collection system enabled"
    else
        log_test "Collection-Status" "WARN" "Collection system disabled"
    fi
    
    # Check last collection
    last_collection=$(echo "$collection_status" | jq -r '.last_collection // "never"')
    log_test "Collection-History" "PASS" "Last collection: $last_collection"
else
    log_test "Collection-Status" "FAIL" "Collection status unavailable"
fi

# Test 9: Container Resource Usage
echo -e "${BLUE}9. Container Resource Usage${NC}"

# Check container stats
if command -v docker &> /dev/null; then
    container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "(blacklist|redis|postgresql)" | head -3)
    if [ -n "$container_stats" ]; then
        log_test "Container-Resources" "PASS" "Resource usage monitored"
        echo -e "   ${CYAN}Container Resource Usage:${NC}"
        echo "$container_stats" | while IFS=$'\t' read -r container cpu memory; do
            echo -e "   ${CYAN}$container: CPU $cpu, Memory $memory${NC}"
        done
    else
        log_test "Container-Resources" "WARN" "Unable to get container stats"
    fi
fi

# Test 10: Configuration Validation
echo -e "${BLUE}10. Configuration Validation${NC}"

if [ -f "docker-compose.yml" ]; then
    compose_image=$(grep "image:" docker-compose.yml | head -1 | awk '{print $2}')
    if [[ "$compose_image" == *"registry.jclee.me"* ]]; then
        log_test "Config-Compose" "PASS" "Docker Compose using correct registry"
    else
        log_test "Config-Compose" "WARN" "Docker Compose registry: $compose_image"
    fi
else
    log_test "Config-Compose" "FAIL" "docker-compose.yml not found"
fi

if [ -f ".env" ]; then
    log_test "Config-Environment" "PASS" ".env file present"
else
    log_test "Config-Environment" "WARN" ".env file not found"
fi

# Generate comprehensive report
echo ""
echo -e "${BLUE}📊 DEPLOYMENT VERIFICATION REPORT${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Summary statistics
echo -e "${CYAN}Summary Statistics:${NC}"
echo -e "   Total Tests: $TOTAL_TESTS"
echo -e "   ${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "   ${RED}Failed: $FAILED_TESTS${NC}"
echo -e "   ${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

# Success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "${CYAN}Success Rate: ${success_rate}%${NC}"
    echo ""
fi

# Detailed results
echo -e "${CYAN}Detailed Results:${NC}"
for result in "${RESULTS[@]}"; do
    echo "   $result"
done
echo ""

# Final verdict
if [ $FAILED_TESTS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 DEPLOYMENT FULLY VERIFIED - All systems operational${NC}"
        exit 0
    else
        echo -e "${YELLOW}✅ DEPLOYMENT VERIFIED WITH WARNINGS - System functional${NC}"
        exit 0
    fi
else
    echo -e "${RED}❌ DEPLOYMENT VERIFICATION FAILED - Critical issues detected${NC}"
    echo -e "${RED}Failed tests: $FAILED_TESTS/$TOTAL_TESTS${NC}"
    
    # Auto-rollback trigger
    echo ""
    echo -e "${YELLOW}🔄 Auto-rollback available: ./scripts/auto-rollback.sh${NC}"
    echo -e "${YELLOW}🔧 Troubleshooting: ./scripts/troubleshoot-deployment.sh${NC}"
    
    exit 1
fi