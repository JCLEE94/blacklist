#!/bin/bash

# Monitoring Services Independence Test Script
# Version: v1.0.37
# Purpose: Test Watchtower, Prometheus, and Grafana monitoring services independently

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
    log "INFO" "Cleaning up monitoring services test..."
    cd "$PROJECT_DIR"
    docker-compose --profile watchtower --profile monitoring down --remove-orphans 2>/dev/null || true
}

# Test Watchtower service
test_watchtower() {
    log "INFO" "Testing Watchtower service..."
    
    cd "$PROJECT_DIR"
    
    # Start Watchtower with profile
    docker-compose --profile watchtower up -d watchtower
    sleep 10
    
    # Check if container is running
    if docker ps --filter "name=blacklist-watchtower" --filter "status=running" | grep -q "blacklist-watchtower"; then
        log "SUCCESS" "Watchtower container is running"
    else
        log "ERROR" "Watchtower container failed to start"
        docker logs blacklist-watchtower 2>/dev/null | tail -10 || true
        return 1
    fi
    
    # Check Watchtower logs for activity
    sleep 15
    local recent_logs=$(docker logs blacklist-watchtower --since=30s 2>/dev/null | head -10 || echo "no_logs")
    if [[ "$recent_logs" != "no_logs" ]]; then
        log "SUCCESS" "Watchtower is generating logs"
        log "INFO" "Recent Watchtower activity:"
        echo "$recent_logs" | head -3
    else
        log "WARNING" "No recent Watchtower logs found"
    fi
    
    # Check Watchtower configuration
    local watchtower_env=$(docker inspect blacklist-watchtower --format='{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null || echo "FAILED")
    if [[ "$watchtower_env" != "FAILED" ]]; then
        if echo "$watchtower_env" | grep -q "WATCHTOWER_SCOPE=blacklist"; then
            log "SUCCESS" "Watchtower scope configuration is correct"
        else
            log "WARNING" "Watchtower scope configuration may be incorrect"
        fi
        
        if echo "$watchtower_env" | grep -q "WATCHTOWER_CLEANUP=true"; then
            log "SUCCESS" "Watchtower cleanup configuration is enabled"
        else
            log "WARNING" "Watchtower cleanup configuration is not enabled"
        fi
    else
        log "WARNING" "Could not inspect Watchtower configuration"
    fi
    
    # Test Watchtower resource usage
    local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" blacklist-watchtower 2>/dev/null || echo "FAILED")
    if [[ "$stats" != "FAILED" ]]; then
        log "SUCCESS" "Watchtower resource monitoring available"
        echo "$stats"
    else
        log "WARNING" "Could not retrieve Watchtower resource stats"
    fi
    
    return 0
}

# Test Prometheus service
test_prometheus() {
    log "INFO" "Testing Prometheus service..."
    
    cd "$PROJECT_DIR"
    
    # Start Prometheus with monitoring profile
    docker-compose --profile monitoring up -d prometheus
    sleep 20
    
    # Check if container is running
    if ! docker ps --filter "name=blacklist-prometheus" --filter "status=running" | grep -q "blacklist-prometheus"; then
        log "ERROR" "Prometheus container failed to start"
        docker logs blacklist-prometheus 2>/dev/null | tail -20 || true
        return 1
    fi
    
    log "SUCCESS" "Prometheus container is running"
    
    # Wait for Prometheus to be ready
    local timeout=60
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if curl -f -s "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
            log "SUCCESS" "Prometheus health endpoint is accessible"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        log "INFO" "Waiting for Prometheus... (${elapsed}/${timeout}s)"
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log "ERROR" "Prometheus failed to become healthy within $timeout seconds"
        docker logs blacklist-prometheus 2>/dev/null | tail -20 || true
        return 1
    fi
    
    # Test Prometheus ready endpoint
    if curl -f -s "http://localhost:9090/-/ready" > /dev/null 2>&1; then
        log "SUCCESS" "Prometheus ready endpoint is accessible"
    else
        log "WARNING" "Prometheus ready endpoint is not accessible (may still be loading)"
    fi
    
    # Test Prometheus API
    local targets_response=$(curl -f -s "http://localhost:9090/api/v1/targets" 2>/dev/null || echo "FAILED")
    if [[ "$targets_response" != "FAILED" ]]; then
        if echo "$targets_response" | jq -e '.status' > /dev/null 2>&1; then
            local api_status=$(echo "$targets_response" | jq -r '.status')
            if [[ "$api_status" == "success" ]]; then
                log "SUCCESS" "Prometheus API is working correctly"
            else
                log "WARNING" "Prometheus API returned status: $api_status"
            fi
        else
            log "WARNING" "Prometheus API response format unexpected"
        fi
    else
        log "WARNING" "Prometheus API targets endpoint not accessible"
    fi
    
    # Test Prometheus query endpoint
    local query_response=$(curl -f -s "http://localhost:9090/api/v1/query?query=up" 2>/dev/null || echo "FAILED")
    if [[ "$query_response" != "FAILED" ]]; then
        if echo "$query_response" | jq -e '.data.result' > /dev/null 2>&1; then
            log "SUCCESS" "Prometheus query endpoint is working"
        else
            log "WARNING" "Prometheus query endpoint response format unexpected"
        fi
    else
        log "WARNING" "Prometheus query endpoint not accessible"
    fi
    
    # Test Prometheus configuration
    local config_response=$(curl -f -s "http://localhost:9090/api/v1/status/config" 2>/dev/null || echo "FAILED")
    if [[ "$config_response" != "FAILED" ]]; then
        log "SUCCESS" "Prometheus configuration endpoint is accessible"
    else
        log "WARNING" "Prometheus configuration endpoint not accessible"
    fi
    
    return 0
}

# Test Grafana service
test_grafana() {
    log "INFO" "Testing Grafana service..."
    
    cd "$PROJECT_DIR"
    
    # Start Grafana with monitoring profile
    docker-compose --profile monitoring up -d grafana
    sleep 25
    
    # Check if container is running
    if ! docker ps --filter "name=blacklist-grafana" --filter "status=running" | grep -q "blacklist-grafana"; then
        log "ERROR" "Grafana container failed to start"
        docker logs blacklist-grafana 2>/dev/null | tail -20 || true
        return 1
    fi
    
    log "SUCCESS" "Grafana container is running"
    
    # Wait for Grafana to be ready
    local timeout=90
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        if curl -f -s "http://localhost:3000/api/health" > /dev/null 2>&1; then
            log "SUCCESS" "Grafana health endpoint is accessible"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        log "INFO" "Waiting for Grafana... (${elapsed}/${timeout}s)"
    done
    
    if [[ $elapsed -ge $timeout ]]; then
        log "ERROR" "Grafana failed to become healthy within $timeout seconds"
        docker logs blacklist-grafana 2>/dev/null | tail -20 || true
        return 1
    fi
    
    # Test Grafana health API
    local health_response=$(curl -f -s "http://localhost:3000/api/health" 2>/dev/null || echo "FAILED")
    if [[ "$health_response" != "FAILED" ]]; then
        if echo "$health_response" | jq -e '.database' > /dev/null 2>&1; then
            local db_status=$(echo "$health_response" | jq -r '.database')
            if [[ "$db_status" == "ok" ]]; then
                log "SUCCESS" "Grafana database is healthy"
            else
                log "WARNING" "Grafana database status: $db_status"
            fi
        else
            log "WARNING" "Grafana health response format unexpected"
        fi
    else
        log "ERROR" "Grafana health endpoint failed"
        return 1
    fi
    
    # Test Grafana login page
    local login_response=$(curl -f -s "http://localhost:3000/login" 2>/dev/null || echo "FAILED")
    if [[ "$login_response" != "FAILED" ]]; then
        if echo "$login_response" | grep -q "Grafana" > /dev/null 2>&1; then
            log "SUCCESS" "Grafana login page is accessible"
        else
            log "WARNING" "Grafana login page may not be fully loaded"
        fi
    else
        log "WARNING" "Grafana login page not accessible"
    fi
    
    # Test Grafana API endpoints
    local datasources_response=$(curl -f -s -u admin:admin "http://localhost:3000/api/datasources" 2>/dev/null || echo "FAILED")
    if [[ "$datasources_response" != "FAILED" ]]; then
        if echo "$datasources_response" | jq -e '.' > /dev/null 2>&1; then
            log "SUCCESS" "Grafana datasources API is working"
        else
            log "WARNING" "Grafana datasources API response format unexpected"
        fi
    else
        log "INFO" "Grafana datasources API not accessible (authentication required)"
    fi
    
    # Test Grafana dashboards endpoint
    local dashboards_response=$(curl -f -s "http://localhost:3000/api/search" 2>/dev/null || echo "FAILED")
    if [[ "$dashboards_response" != "FAILED" ]]; then
        if echo "$dashboards_response" | jq -e '.' > /dev/null 2>&1; then
            log "SUCCESS" "Grafana dashboards API is working"
        else
            log "WARNING" "Grafana dashboards API response format unexpected"
        fi
    else
        log "WARNING" "Grafana dashboards API not accessible"
    fi
    
    return 0
}

# Test all monitoring services together
test_monitoring_integration() {
    log "INFO" "Testing monitoring services integration..."
    
    cd "$PROJECT_DIR"
    
    # Start all monitoring services
    docker-compose --profile watchtower --profile monitoring up -d
    sleep 30
    
    # Check if all containers are running
    local services=("blacklist-watchtower" "blacklist-prometheus" "blacklist-grafana")
    local running_services=0
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            log "SUCCESS" "$service is running"
            ((running_services++))
        else
            log "WARNING" "$service is not running"
        fi
    done
    
    log "INFO" "Running monitoring services: $running_services/${#services[@]}"
    
    # Test service interdependencies
    if [[ $running_services -ge 2 ]]; then
        # Test if Grafana can connect to Prometheus (if both are running)
        if docker ps --filter "name=blacklist-prometheus" --filter "status=running" | grep -q "blacklist-prometheus" && 
           docker ps --filter "name=blacklist-grafana" --filter "status=running" | grep -q "blacklist-grafana"; then
            
            # Wait a bit more for services to fully initialize
            sleep 20
            
            # Test Prometheus from Grafana's perspective (via Docker network)
            if docker exec blacklist-grafana wget -q -O - http://blacklist-prometheus:9090/-/healthy > /dev/null 2>&1; then
                log "SUCCESS" "Grafana can reach Prometheus via Docker network"
            else
                log "WARNING" "Grafana cannot reach Prometheus via Docker network"
            fi
        fi
    fi
    
    # Test resource usage of monitoring stack
    log "INFO" "Monitoring stack resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" "${services[@]}" 2>/dev/null || log "WARNING" "Could not retrieve monitoring stack resource stats"
    
    if [[ $running_services -eq ${#services[@]} ]]; then
        log "SUCCESS" "All monitoring services are running and integrated"
        return 0
    else
        log "WARNING" "Not all monitoring services are running ($running_services/${#services[@]})"
        return 0  # Non-critical for independence test
    fi
}

# Main test function
run_monitoring_test() {
    local test_service=${1:-"all"}
    local test_results=()
    
    log "INFO" "Starting monitoring services independence test..."
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    case $test_service in
        "watchtower")
            if test_watchtower; then
                test_results+=("watchtower:PASS")
            else
                test_results+=("watchtower:FAIL")
            fi
            ;;
        "prometheus")
            if test_prometheus; then
                test_results+=("prometheus:PASS")
            else
                test_results+=("prometheus:FAIL")
            fi
            ;;
        "grafana")
            if test_grafana; then
                test_results+=("grafana:PASS")
            else
                test_results+=("grafana:FAIL")
            fi
            ;;
        "all"|*)
            log "INFO" "Testing all monitoring services..."
            
            # Test Watchtower
            if test_watchtower; then
                test_results+=("watchtower:PASS")
            else
                test_results+=("watchtower:FAIL")
            fi
            
            cleanup
            sleep 5
            
            # Test Prometheus
            if test_prometheus; then
                test_results+=("prometheus:PASS")
            else
                test_results+=("prometheus:FAIL")
            fi
            
            cleanup
            sleep 5
            
            # Test Grafana
            if test_grafana; then
                test_results+=("grafana:PASS")
            else
                test_results+=("grafana:FAIL")
            fi
            
            cleanup
            sleep 5
            
            # Test integration
            if test_monitoring_integration; then
                test_results+=("integration:PASS")
            else
                test_results+=("integration:FAIL")
            fi
            ;;
    esac
    
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
        log "SUCCESS" "All monitoring service tests passed!"
        return 0
    else
        log "ERROR" "$failed_tests out of $total_tests tests failed"
        return 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SERVICE]

Test monitoring services for independence and functionality.

OPTIONS:
    --help              Show this help message

SERVICES:
    watchtower          Test Watchtower auto-update service only
    prometheus          Test Prometheus monitoring service only
    grafana             Test Grafana visualization service only
    all                 Test all monitoring services (default)

EXAMPLES:
    $0                  # Test all monitoring services
    $0 watchtower       # Test Watchtower only
    $0 prometheus       # Test Prometheus only
    $0 grafana          # Test Grafana only

EOF
}

# Main execution
main() {
    local test_service="all"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                exit 0
                ;;
            watchtower|prometheus|grafana|all)
                test_service=$1
                shift
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if run_monitoring_test "$test_service"; then
        echo -e "\n${GREEN}✅ Monitoring services independence test completed successfully${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Monitoring services independence test failed${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"