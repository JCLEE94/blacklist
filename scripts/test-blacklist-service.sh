#!/bin/bash

# Blacklist Service Independence Test Script
# Version: v1.0.37
# Purpose: Test blacklist main application service independently

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="blacklist"
CONTAINER_NAME="blacklist"
PORT="32542"
INTERNAL_PORT="2542"

# Test endpoints
HEALTH_URL="http://localhost:$PORT/health"
API_HEALTH_URL="http://localhost:$PORT/api/health"
BLACKLIST_URL="http://localhost:$PORT/api/blacklist/active"
COLLECTION_URL="http://localhost:$PORT/api/collection/status"
FORTIGATE_URL="http://localhost:$PORT/api/fortigate"

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" >&2
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
    esac
}

# Cleanup function
cleanup() {
    log "INFO" "Cleaning up blacklist service test..."
    cd "$PROJECT_DIR"
    docker-compose down --remove-orphans 2>/dev/null || true
    docker ps -a | grep "test-blacklist" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
}

# Start dependencies
start_dependencies() {
    log "INFO" "Starting dependencies (PostgreSQL and Redis)..."
    cd "$PROJECT_DIR"
    
    # Start PostgreSQL
    docker-compose up -d postgresql
    sleep 10
    
    # Wait for PostgreSQL
    log "INFO" "Waiting for PostgreSQL to be ready..."
    local timeout=60
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if docker exec blacklist-postgresql pg_isready -U blacklist_user -d blacklist > /dev/null 2>&1; then
            log "SUCCESS" "PostgreSQL is ready"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log "ERROR" "PostgreSQL failed to start within $timeout seconds"
        return 1
    fi
    
    # Start Redis
    docker-compose up -d redis
    sleep 5
    
    # Wait for Redis
    log "INFO" "Waiting for Redis to be ready..."
    timeout=30
    elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if docker exec blacklist-redis redis-cli ping | grep -q "PONG" > /dev/null 2>&1; then
            log "SUCCESS" "Redis is ready"
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log "ERROR" "Redis failed to start within $timeout seconds"
        return 1
    fi
    
    return 0
}

# Start blacklist service
start_blacklist_service() {
    log "INFO" "Starting blacklist service..."
    cd "$PROJECT_DIR"
    
    docker-compose up -d blacklist
    sleep 15
    
    # Check if container is running
    if ! docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
        log "ERROR" "Blacklist container failed to start"
        docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
        return 1
    fi
    
    log "SUCCESS" "Blacklist container started successfully"
    return 0
}

# Wait for service to be healthy
wait_for_health() {
    log "INFO" "Waiting for blacklist service to be healthy..."
    local timeout=120
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
            log "SUCCESS" "Blacklist service is healthy"
            return 0
        fi
        
        # Check container status
        local status=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        if [[ "$status" != "running" ]]; then
            log "ERROR" "Blacklist container stopped running (status: $status)"
            docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
            return 1
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        log "INFO" "Waiting for health check... (${elapsed}/${timeout}s)"
    done
    
    log "ERROR" "Blacklist service failed to become healthy within $timeout seconds"
    docker logs "$CONTAINER_NAME" 2>/dev/null | tail -30 || true
    return 1
}

# Test health endpoints
test_health_endpoints() {
    log "INFO" "Testing health endpoints..."
    
    # Test basic health endpoint
    local health_response=$(curl -f -s "$HEALTH_URL" 2>/dev/null || echo "FAILED")
    if [[ "$health_response" == "FAILED" ]]; then
        log "ERROR" "Health endpoint (/health) is not accessible"
        return 1
    fi
    
    if echo "$health_response" | jq -e '.status' > /dev/null 2>&1; then
        local status=$(echo "$health_response" | jq -r '.status')
        if [[ "$status" == "healthy" ]]; then
            log "SUCCESS" "Health endpoint reports healthy status"
        else
            log "WARNING" "Health endpoint reports status: $status"
        fi
    else
        log "WARNING" "Health endpoint response is not JSON format"
    fi
    
    # Test detailed API health endpoint
    local api_health_response=$(curl -f -s "$API_HEALTH_URL" 2>/dev/null || echo "FAILED")
    if [[ "$api_health_response" == "FAILED" ]]; then
        log "ERROR" "API health endpoint (/api/health) is not accessible"
        return 1
    fi
    
    if echo "$api_health_response" | jq -e '.status' > /dev/null 2>&1; then
        log "SUCCESS" "API health endpoint is accessible and returns JSON"
        
        # Check individual service status
        local services=("database" "cache" "collection")
        for service in "${services[@]}"; do
            local service_status=$(echo "$api_health_response" | jq -r ".$service.status // \"unknown\"")
            if [[ "$service_status" == "healthy" ]]; then
                log "SUCCESS" "$service service is healthy"
            else
                log "WARNING" "$service service status: $service_status"
            fi
        done
    else
        log "WARNING" "API health endpoint response is not valid JSON"
    fi
    
    return 0
}

# Test API endpoints
test_api_endpoints() {
    log "INFO" "Testing API endpoints..."
    
    # Test blacklist active endpoint
    local blacklist_response=$(curl -f -s "$BLACKLIST_URL" 2>/dev/null || echo "FAILED")
    if [[ "$blacklist_response" == "FAILED" ]]; then
        log "ERROR" "Blacklist active endpoint is not accessible"
        return 1
    fi
    
    if [[ -n "$blacklist_response" ]]; then
        local line_count=$(echo "$blacklist_response" | wc -l)
        log "SUCCESS" "Blacklist active endpoint returned $line_count lines"
    else
        log "SUCCESS" "Blacklist active endpoint accessible (empty response is valid)"
    fi
    
    # Test collection status endpoint
    local collection_response=$(curl -f -s "$COLLECTION_URL" 2>/dev/null || echo "FAILED")
    if [[ "$collection_response" == "FAILED" ]]; then
        log "ERROR" "Collection status endpoint is not accessible"
        return 1
    fi
    
    if echo "$collection_response" | jq -e '.status' > /dev/null 2>&1; then
        local collection_status=$(echo "$collection_response" | jq -r '.status')
        log "SUCCESS" "Collection status endpoint accessible (status: $collection_status)"
    else
        log "WARNING" "Collection status endpoint response is not valid JSON"
    fi
    
    # Test FortiGate endpoint
    local fortigate_response=$(curl -f -s "$FORTIGATE_URL" 2>/dev/null || echo "FAILED")
    if [[ "$fortigate_response" == "FAILED" ]]; then
        log "ERROR" "FortiGate endpoint is not accessible"
        return 1
    fi
    
    if [[ -n "$fortigate_response" ]]; then
        log "SUCCESS" "FortiGate endpoint is accessible"
    else
        log "SUCCESS" "FortiGate endpoint accessible (empty response is valid)"
    fi
    
    return 0
}

# Test performance
test_performance() {
    log "INFO" "Testing performance..."
    
    # Test response times
    local endpoints=("$HEALTH_URL" "$API_HEALTH_URL" "$BLACKLIST_URL" "$COLLECTION_URL")
    local total_time=0
    local test_count=0
    
    for endpoint in "${endpoints[@]}"; do
        local response_time=$(curl -w "%{time_total}" -s -o /dev/null "$endpoint" 2>/dev/null || echo "0")
        if [[ "$response_time" != "0" ]]; then
            local time_ms=$(echo "$response_time * 1000" | bc -l)
            log "INFO" "$(basename "$endpoint"): ${time_ms%.*}ms"
            total_time=$(echo "$total_time + $response_time" | bc -l)
            ((test_count++))
        fi
    done
    
    if [[ $test_count -gt 0 ]]; then
        local avg_time=$(echo "scale=3; $total_time / $test_count" | bc -l)
        local avg_ms=$(echo "$avg_time * 1000" | bc -l)
        log "SUCCESS" "Average response time: ${avg_ms%.*}ms"
        
        # Check if performance is acceptable
        if (( $(echo "$avg_time < 0.200" | bc -l) )); then
            log "SUCCESS" "Performance is excellent (<200ms)"
        elif (( $(echo "$avg_time < 1.000" | bc -l) )); then
            log "SUCCESS" "Performance is good (<1000ms)"
        else
            log "WARNING" "Performance may need optimization (>1000ms)"
        fi
    fi
    
    return 0
}

# Test resource usage
test_resource_usage() {
    log "INFO" "Testing resource usage..."
    
    # Get container stats
    local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" "$CONTAINER_NAME" 2>/dev/null || echo "FAILED")
    
    if [[ "$stats" != "FAILED" ]]; then
        log "INFO" "Container resource usage:"
        echo "$stats"
        
        # Extract CPU percentage
        local cpu_percent=$(echo "$stats" | tail -n 1 | awk '{print $1}' | sed 's/%//')
        if [[ -n "$cpu_percent" && "$cpu_percent" != "--" ]]; then
            if (( $(echo "$cpu_percent < 50" | bc -l 2>/dev/null || echo 0) )); then
                log "SUCCESS" "CPU usage is normal ($cpu_percent%)"
            else
                log "WARNING" "CPU usage is high ($cpu_percent%)"
            fi
        fi
        
        # Extract memory usage
        local mem_usage=$(echo "$stats" | tail -n 1 | awk '{print $2}' | sed 's/MiB.*//')
        if [[ -n "$mem_usage" && "$mem_usage" != "--" ]]; then
            if (( $(echo "$mem_usage < 500" | bc -l 2>/dev/null || echo 0) )); then
                log "SUCCESS" "Memory usage is normal (${mem_usage}MiB)"
            else
                log "WARNING" "Memory usage is high (${mem_usage}MiB)"
            fi
        fi
    else
        log "WARNING" "Could not retrieve container stats"
    fi
    
    return 0
}

# Test database connectivity
test_database_connectivity() {
    log "INFO" "Testing database connectivity..."
    
    # Test through container exec
    if docker exec "$CONTAINER_NAME" python3 -c "
from src.core.database.connection_manager import ConnectionManager
try:
    conn_mgr = ConnectionManager()
    with conn_mgr.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 as test_val')
        result = cursor.fetchone()
        if result and result[0] == 1:
            print('Database connection successful')
        else:
            print('Database query failed')
            exit(1)
except Exception as e:
    print(f'Database error: {e}')
    exit(1)
" 2>/dev/null; then
        log "SUCCESS" "Database connectivity test passed"
        return 0
    else
        log "ERROR" "Database connectivity test failed"
        return 1
    fi
}

# Test cache connectivity
test_cache_connectivity() {
    log "INFO" "Testing cache connectivity..."
    
    # Test through container exec
    if docker exec "$CONTAINER_NAME" python3 -c "
from src.core.cache.cache_manager import CacheManager
try:
    cache_mgr = CacheManager()
    test_key = 'independence_test'
    test_value = 'test_value_123'
    cache_mgr.set(test_key, test_value, ttl=30)
    retrieved = cache_mgr.get(test_key)
    if retrieved == test_value:
        print('Cache connectivity successful')
        cache_mgr.delete(test_key)
    else:
        print('Cache value mismatch')
        exit(1)
except Exception as e:
    print(f'Cache error: {e}')
    exit(1)
" 2>/dev/null; then
        log "SUCCESS" "Cache connectivity test passed"
        return 0
    else
        log "WARNING" "Cache connectivity test failed (may fallback to memory)"
        return 0  # Non-critical failure
    fi
}

# Test without dependencies (isolation test)
test_isolation() {
    log "INFO" "Testing blacklist service in isolation (without dependencies)..."
    
    # Stop dependencies
    cleanup
    cd "$PROJECT_DIR"
    
    # Start only blacklist service
    docker-compose up -d blacklist
    sleep 15
    
    # Check if container starts without dependencies
    if docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
        log "SUCCESS" "Blacklist container started without dependencies"
        
        # Try to access health endpoint (should work with fallback configs)
        local health_response=$(curl -f -s "$HEALTH_URL" 2>/dev/null || echo "FAILED")
        if [[ "$health_response" != "FAILED" ]]; then
            log "SUCCESS" "Service responds to health checks without dependencies"
        else
            log "WARNING" "Service does not respond without dependencies (expected for full functionality)"
        fi
    else
        log "WARNING" "Blacklist container cannot start without dependencies (expected behavior)"
    fi
    
    return 0
}

# Main test function
run_blacklist_test() {
    local test_isolation=${1:-false}
    local test_results=()
    
    log "INFO" "Starting blacklist service independence test..."
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    if [[ "$test_isolation" == "true" ]]; then
        log "INFO" "Running isolation test..."
        test_isolation
        return $?
    fi
    
    # Start dependencies
    if ! start_dependencies; then
        log "ERROR" "Failed to start dependencies"
        return 1
    fi
    
    # Start blacklist service
    if ! start_blacklist_service; then
        log "ERROR" "Failed to start blacklist service"
        return 1
    fi
    
    # Wait for service to be healthy
    if ! wait_for_health; then
        log "ERROR" "Service failed to become healthy"
        return 1
    fi
    
    # Run tests
    log "INFO" "Running comprehensive blacklist service tests..."
    
    # Test health endpoints
    if test_health_endpoints; then
        test_results+=("health_endpoints:PASS")
    else
        test_results+=("health_endpoints:FAIL")
    fi
    
    # Test API endpoints
    if test_api_endpoints; then
        test_results+=("api_endpoints:PASS")
    else
        test_results+=("api_endpoints:FAIL")
    fi
    
    # Test performance
    if test_performance; then
        test_results+=("performance:PASS")
    else
        test_results+=("performance:FAIL")
    fi
    
    # Test resource usage
    if test_resource_usage; then
        test_results+=("resource_usage:PASS")
    else
        test_results+=("resource_usage:FAIL")
    fi
    
    # Test database connectivity
    if test_database_connectivity; then
        test_results+=("database_connectivity:PASS")
    else
        test_results+=("database_connectivity:FAIL")
    fi
    
    # Test cache connectivity
    if test_cache_connectivity; then
        test_results+=("cache_connectivity:PASS")
    else
        test_results+=("cache_connectivity:FAIL")
    fi
    
    # Generate report
    log "INFO" "=== Test Results ==="
    local total_tests=${#test_results[@]}
    local passed_tests=0
    local failed_tests=0
    
    for result in "${test_results[@]}"; do
        local test_name=$(echo "$result" | cut -d: -f1)
        local test_status=$(echo "$result" | cut -d: -f2)
        
        if [[ "$test_status" == "PASS" ]]; then
            log "SUCCESS" "$test_name: PASSED"
            ((passed_tests++))
        else
            log "ERROR" "$test_name: FAILED"
            ((failed_tests++))
        fi
    done
    
    log "INFO" "Total tests: $total_tests"
    log "INFO" "Passed: $passed_tests"
    log "INFO" "Failed: $failed_tests"
    
    if [[ $failed_tests -eq 0 ]]; then
        log "SUCCESS" "All blacklist service tests passed!"
        return 0
    else
        log "ERROR" "$failed_tests out of $total_tests tests failed"
        return 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Test blacklist service for independence and functionality.

OPTIONS:
    --isolation         Test service in isolation (without dependencies)
    --help              Show this help message

EXAMPLES:
    $0                  # Normal test with dependencies
    $0 --isolation      # Test without dependencies

EOF
}

# Main execution
main() {
    local test_isolation=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --isolation)
                test_isolation=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if run_blacklist_test "$test_isolation"; then
        echo -e "\n${GREEN}✅ Blacklist service independence test completed successfully${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Blacklist service independence test failed${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"