#!/bin/bash

# Redis Service Independence Test Script
# Version: v1.0.37
# Purpose: Test Redis cache service independently

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
SERVICE_NAME="redis"
CONTAINER_NAME="blacklist-redis"
PORT="32543"
INTERNAL_PORT="6379"

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
    log "INFO" "Cleaning up Redis service test..."
    cd "$PROJECT_DIR"
    docker-compose stop redis 2>/dev/null || true
    docker-compose rm -f redis 2>/dev/null || true
}

# Start Redis service
start_redis_service() {
    log "INFO" "Starting Redis service..."
    cd "$PROJECT_DIR"
    
    docker-compose up -d redis
    sleep 10
    
    # Check if container is running
    if ! docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
        log "ERROR" "Redis container failed to start"
        docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
        return 1
    fi
    
    log "SUCCESS" "Redis container started successfully"
    return 0
}

# Wait for Redis to be ready
wait_for_redis() {
    log "INFO" "Waiting for Redis to be ready..."
    local timeout=60
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if docker exec "$CONTAINER_NAME" redis-cli ping | grep -q "PONG" > /dev/null 2>&1; then
            log "SUCCESS" "Redis is ready and responding to ping"
            return 0
        fi
        
        # Check container status
        local status=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        if [[ "$status" != "running" ]]; then
            log "ERROR" "Redis container stopped running (status: $status)"
            docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
            return 1
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
        log "INFO" "Waiting for Redis... (${elapsed}/${timeout}s)"
    done
    
    log "ERROR" "Redis failed to become ready within $timeout seconds"
    docker logs "$CONTAINER_NAME" 2>/dev/null | tail -30 || true
    return 1
}

# Test basic Redis operations
test_basic_operations() {
    log "INFO" "Testing basic Redis operations..."
    
    # Test PING
    if docker exec "$CONTAINER_NAME" redis-cli ping | grep -q "PONG"; then
        log "SUCCESS" "PING command successful"
    else
        log "ERROR" "PING command failed"
        return 1
    fi
    
    # Test SET operation
    local test_key="independence_test_$(date +%s)"
    local test_value="redis_test_value_123"
    
    if docker exec "$CONTAINER_NAME" redis-cli set "$test_key" "$test_value" | grep -q "OK"; then
        log "SUCCESS" "SET operation successful"
    else
        log "ERROR" "SET operation failed"
        return 1
    fi
    
    # Test GET operation
    local retrieved_value=$(docker exec "$CONTAINER_NAME" redis-cli get "$test_key")
    if [[ "$retrieved_value" == "$test_value" ]]; then
        log "SUCCESS" "GET operation successful (value: $retrieved_value)"
    else
        log "ERROR" "GET operation failed. Expected: $test_value, Got: $retrieved_value"
        return 1
    fi
    
    # Test DEL operation
    if docker exec "$CONTAINER_NAME" redis-cli del "$test_key" | grep -q "1"; then
        log "SUCCESS" "DEL operation successful"
    else
        log "ERROR" "DEL operation failed"
        return 1
    fi
    
    # Test EXISTS operation
    local exists_result=$(docker exec "$CONTAINER_NAME" redis-cli exists "$test_key")
    if [[ "$exists_result" == "0" ]]; then
        log "SUCCESS" "EXISTS operation confirms key deletion"
    else
        log "ERROR" "EXISTS operation shows key still exists after deletion"
        return 1
    fi
    
    return 0
}

# Test data types and operations
test_data_types() {
    log "INFO" "Testing Redis data types..."
    
    local base_key="independence_test_$(date +%s)"
    
    # Test String operations
    local string_key="${base_key}_string"
    docker exec "$CONTAINER_NAME" redis-cli set "$string_key" "test_string" > /dev/null
    docker exec "$CONTAINER_NAME" redis-cli append "$string_key" "_appended" > /dev/null
    local string_result=$(docker exec "$CONTAINER_NAME" redis-cli get "$string_key")
    if [[ "$string_result" == "test_string_appended" ]]; then
        log "SUCCESS" "String operations (SET, APPEND, GET) working"
    else
        log "ERROR" "String operations failed"
        return 1
    fi
    
    # Test List operations
    local list_key="${base_key}_list"
    docker exec "$CONTAINER_NAME" redis-cli lpush "$list_key" "item1" "item2" "item3" > /dev/null
    local list_length=$(docker exec "$CONTAINER_NAME" redis-cli llen "$list_key")
    if [[ "$list_length" == "3" ]]; then
        log "SUCCESS" "List operations (LPUSH, LLEN) working"
    else
        log "ERROR" "List operations failed (length: $list_length)"
        return 1
    fi
    
    # Test Hash operations
    local hash_key="${base_key}_hash"
    docker exec "$CONTAINER_NAME" redis-cli hset "$hash_key" "field1" "value1" "field2" "value2" > /dev/null
    local hash_length=$(docker exec "$CONTAINER_NAME" redis-cli hlen "$hash_key")
    if [[ "$hash_length" == "2" ]]; then
        log "SUCCESS" "Hash operations (HSET, HLEN) working"
    else
        log "ERROR" "Hash operations failed (length: $hash_length)"
        return 1
    fi
    
    # Test Set operations
    local set_key="${base_key}_set"
    docker exec "$CONTAINER_NAME" redis-cli sadd "$set_key" "member1" "member2" "member3" > /dev/null
    local set_size=$(docker exec "$CONTAINER_NAME" redis-cli scard "$set_key")
    if [[ "$set_size" == "3" ]]; then
        log "SUCCESS" "Set operations (SADD, SCARD) working"
    else
        log "ERROR" "Set operations failed (size: $set_size)"
        return 1
    fi
    
    # Cleanup test keys
    docker exec "$CONTAINER_NAME" redis-cli del "$string_key" "$list_key" "$hash_key" "$set_key" > /dev/null
    
    return 0
}

# Test TTL and expiration
test_expiration() {
    log "INFO" "Testing TTL and expiration functionality..."
    
    local ttl_key="independence_test_ttl_$(date +%s)"
    
    # Set key with TTL
    docker exec "$CONTAINER_NAME" redis-cli setex "$ttl_key" 10 "expires_in_10_seconds" > /dev/null
    
    # Check initial TTL
    local initial_ttl=$(docker exec "$CONTAINER_NAME" redis-cli ttl "$ttl_key")
    if [[ "$initial_ttl" -gt 0 && "$initial_ttl" -le 10 ]]; then
        log "SUCCESS" "TTL set correctly (initial TTL: ${initial_ttl}s)"
    else
        log "ERROR" "TTL not set correctly (TTL: $initial_ttl)"
        return 1
    fi
    
    # Wait a bit and check TTL again
    sleep 3
    local updated_ttl=$(docker exec "$CONTAINER_NAME" redis-cli ttl "$ttl_key")
    if [[ "$updated_ttl" -gt 0 && "$updated_ttl" -lt "$initial_ttl" ]]; then
        log "SUCCESS" "TTL is counting down correctly (current TTL: ${updated_ttl}s)"
    else
        log "ERROR" "TTL not counting down correctly (TTL: $updated_ttl)"
        return 1
    fi
    
    # Test EXPIRE command
    docker exec "$CONTAINER_NAME" redis-cli set "${ttl_key}_2" "test_expire" > /dev/null
    docker exec "$CONTAINER_NAME" redis-cli expire "${ttl_key}_2" 5 > /dev/null
    local expire_ttl=$(docker exec "$CONTAINER_NAME" redis-cli ttl "${ttl_key}_2")
    if [[ "$expire_ttl" -gt 0 && "$expire_ttl" -le 5 ]]; then
        log "SUCCESS" "EXPIRE command working (TTL: ${expire_ttl}s)"
    else
        log "ERROR" "EXPIRE command failed (TTL: $expire_ttl)"
        return 1
    fi
    
    # Cleanup
    docker exec "$CONTAINER_NAME" redis-cli del "$ttl_key" "${ttl_key}_2" > /dev/null 2>&1 || true
    
    return 0
}

# Test persistence
test_persistence() {
    log "INFO" "Testing Redis persistence..."
    
    local persist_key="independence_test_persist_$(date +%s)"
    local persist_value="persistent_data_123"
    
    # Set a key
    docker exec "$CONTAINER_NAME" redis-cli set "$persist_key" "$persist_value" > /dev/null
    
    # Force a save
    if docker exec "$CONTAINER_NAME" redis-cli bgsave | grep -q "Background saving started"; then
        log "SUCCESS" "Background save initiated successfully"
    else
        log "WARNING" "Background save may have failed (non-critical)"
    fi
    
    # Check if LASTSAVE command works
    local last_save=$(docker exec "$CONTAINER_NAME" redis-cli lastsave)
    if [[ -n "$last_save" && "$last_save" != "0" ]]; then
        log "SUCCESS" "Persistence is configured (last save timestamp: $last_save)"
    else
        log "WARNING" "Cannot verify persistence configuration"
    fi
    
    # Cleanup
    docker exec "$CONTAINER_NAME" redis-cli del "$persist_key" > /dev/null
    
    return 0
}

# Test memory and configuration
test_memory_config() {
    log "INFO" "Testing Redis memory and configuration..."
    
    # Check memory usage
    local memory_info=$(docker exec "$CONTAINER_NAME" redis-cli info memory 2>/dev/null || echo "FAILED")
    if [[ "$memory_info" != "FAILED" ]]; then
        local used_memory=$(echo "$memory_info" | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
        local max_memory=$(echo "$memory_info" | grep "maxmemory_human:" | cut -d: -f2 | tr -d '\r')
        
        if [[ -n "$used_memory" ]]; then
            log "SUCCESS" "Memory info accessible (used: $used_memory, max: ${max_memory:-unlimited})"
        else
            log "WARNING" "Could not parse memory information"
        fi
    else
        log "ERROR" "Could not retrieve memory information"
        return 1
    fi
    
    # Check configuration
    local config_info=$(docker exec "$CONTAINER_NAME" redis-cli config get maxmemory 2>/dev/null || echo "FAILED")
    if [[ "$config_info" != "FAILED" ]]; then
        log "SUCCESS" "Configuration commands working"
    else
        log "ERROR" "Configuration commands failed"
        return 1
    fi
    
    # Test client connection info
    local client_info=$(docker exec "$CONTAINER_NAME" redis-cli info clients 2>/dev/null || echo "FAILED")
    if [[ "$client_info" != "FAILED" ]]; then
        local connected_clients=$(echo "$client_info" | grep "connected_clients:" | cut -d: -f2 | tr -d '\r')
        if [[ -n "$connected_clients" ]]; then
            log "SUCCESS" "Client info accessible (connected clients: $connected_clients)"
        else
            log "WARNING" "Could not parse client information"
        fi
    else
        log "ERROR" "Could not retrieve client information"
        return 1
    fi
    
    return 0
}

# Test performance
test_performance() {
    log "INFO" "Testing Redis performance..."
    
    local performance_key="perf_test_$(date +%s)"
    local test_iterations=1000
    
    # Measure SET performance
    local start_time=$(date +%s.%N)
    for ((i=1; i<=test_iterations; i++)); do
        docker exec "$CONTAINER_NAME" redis-cli set "${performance_key}_$i" "value_$i" > /dev/null
    done
    local set_end_time=$(date +%s.%N)
    local set_duration=$(echo "$set_end_time - $start_time" | bc -l)
    local set_ops_per_sec=$(echo "scale=2; $test_iterations / $set_duration" | bc -l)
    
    log "SUCCESS" "SET performance: ${set_ops_per_sec} ops/sec ($test_iterations operations in ${set_duration}s)"
    
    # Measure GET performance
    start_time=$(date +%s.%N)
    for ((i=1; i<=test_iterations; i++)); do
        docker exec "$CONTAINER_NAME" redis-cli get "${performance_key}_$i" > /dev/null
    done
    local get_end_time=$(date +%s.%N)
    local get_duration=$(echo "$get_end_time - $start_time" | bc -l)
    local get_ops_per_sec=$(echo "scale=2; $test_iterations / $get_duration" | bc -l)
    
    log "SUCCESS" "GET performance: ${get_ops_per_sec} ops/sec ($test_iterations operations in ${get_duration}s)"
    
    # Cleanup performance test keys
    for ((i=1; i<=test_iterations; i++)); do
        docker exec "$CONTAINER_NAME" redis-cli del "${performance_key}_$i" > /dev/null 2>&1 || true
    done
    
    # Check if performance is acceptable
    if (( $(echo "$set_ops_per_sec > 100" | bc -l) )) && (( $(echo "$get_ops_per_sec > 100" | bc -l) )); then
        log "SUCCESS" "Performance is acceptable (>100 ops/sec for both SET and GET)"
        return 0
    else
        log "WARNING" "Performance may be suboptimal (<100 ops/sec)"
        return 0  # Non-critical
    fi
}

# Test resource usage
test_resource_usage() {
    log "INFO" "Testing Redis resource usage..."
    
    # Get container stats
    local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" "$CONTAINER_NAME" 2>/dev/null || echo "FAILED")
    
    if [[ "$stats" != "FAILED" ]]; then
        log "INFO" "Redis container resource usage:"
        echo "$stats"
        
        # Extract CPU percentage
        local cpu_percent=$(echo "$stats" | tail -n 1 | awk '{print $1}' | sed 's/%//')
        if [[ -n "$cpu_percent" && "$cpu_percent" != "--" ]]; then
            if (( $(echo "$cpu_percent < 10" | bc -l 2>/dev/null || echo 0) )); then
                log "SUCCESS" "CPU usage is normal ($cpu_percent%)"
            else
                log "WARNING" "CPU usage is elevated ($cpu_percent%)"
            fi
        fi
        
        # Extract memory usage
        local mem_usage=$(echo "$stats" | tail -n 1 | awk '{print $2}' | sed 's/MiB.*//')
        if [[ -n "$mem_usage" && "$mem_usage" != "--" ]]; then
            if (( $(echo "$mem_usage < 200" | bc -l 2>/dev/null || echo 0) )); then
                log "SUCCESS" "Memory usage is normal (${mem_usage}MiB)"
            else
                log "WARNING" "Memory usage is elevated (${mem_usage}MiB)"
            fi
        fi
    else
        log "WARNING" "Could not retrieve container stats"
    fi
    
    return 0
}

# Test network connectivity
test_network_connectivity() {
    log "INFO" "Testing Redis network connectivity..."
    
    # Test local redis-cli connection
    if docker exec "$CONTAINER_NAME" redis-cli -h 127.0.0.1 -p 6379 ping | grep -q "PONG"; then
        log "SUCCESS" "Local network connectivity working"
    else
        log "ERROR" "Local network connectivity failed"
        return 1
    fi
    
    # Test external connection (if port is exposed)
    if command -v redis-cli > /dev/null 2>&1; then
        if redis-cli -h localhost -p "$PORT" ping 2>/dev/null | grep -q "PONG"; then
            log "SUCCESS" "External network connectivity working (port $PORT)"
        else
            log "WARNING" "External network connectivity not working (port $PORT may not be exposed)"
        fi
    else
        log "INFO" "redis-cli not available on host, skipping external connectivity test"
    fi
    
    return 0
}

# Main test function
run_redis_test() {
    local test_results=()
    
    log "INFO" "Starting Redis service independence test..."
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    # Start Redis service
    if ! start_redis_service; then
        log "ERROR" "Failed to start Redis service"
        return 1
    fi
    
    # Wait for service to be ready
    if ! wait_for_redis; then
        log "ERROR" "Redis service failed to become ready"
        return 1
    fi
    
    # Run tests
    log "INFO" "Running comprehensive Redis service tests..."
    
    # Test basic operations
    if test_basic_operations; then
        test_results+=("basic_operations:PASS")
    else
        test_results+=("basic_operations:FAIL")
    fi
    
    # Test data types
    if test_data_types; then
        test_results+=("data_types:PASS")
    else
        test_results+=("data_types:FAIL")
    fi
    
    # Test expiration
    if test_expiration; then
        test_results+=("expiration:PASS")
    else
        test_results+=("expiration:FAIL")
    fi
    
    # Test persistence
    if test_persistence; then
        test_results+=("persistence:PASS")
    else
        test_results+=("persistence:FAIL")
    fi
    
    # Test memory and configuration
    if test_memory_config; then
        test_results+=("memory_config:PASS")
    else
        test_results+=("memory_config:FAIL")
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
    
    # Test network connectivity
    if test_network_connectivity; then
        test_results+=("network_connectivity:PASS")
    else
        test_results+=("network_connectivity:FAIL")
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
        log "SUCCESS" "All Redis service tests passed!"
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

Test Redis service for independence and functionality.

OPTIONS:
    --help              Show this help message

EXAMPLES:
    $0                  # Run Redis independence test

EOF
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
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
    
    if run_redis_test; then
        echo -e "\n${GREEN}✅ Redis service independence test completed successfully${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Redis service independence test failed${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"