#!/bin/bash

# PostgreSQL Service Independence Test Script
# Version: v1.0.37
# Purpose: Test PostgreSQL database service independently

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
SERVICE_NAME="postgresql"
CONTAINER_NAME="blacklist-postgresql"
PORT="32544"
INTERNAL_PORT="5432"

# Database configuration
DB_NAME="blacklist"
DB_USER="blacklist_user"
DB_PASSWORD="${POSTGRES_PASSWORD:-blacklist_password_change_me}"

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
    log "INFO" "Cleaning up PostgreSQL service test..."
    cd "$PROJECT_DIR"
    docker-compose stop postgresql 2>/dev/null || true
    docker-compose rm -f postgresql 2>/dev/null || true
}

# Start PostgreSQL service
start_postgresql_service() {
    log "INFO" "Starting PostgreSQL service..."
    cd "$PROJECT_DIR"
    
    docker-compose up -d postgresql
    sleep 15
    
    # Check if container is running
    if ! docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
        log "ERROR" "PostgreSQL container failed to start"
        docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
        return 1
    fi
    
    log "SUCCESS" "PostgreSQL container started successfully"
    return 0
}

# Wait for PostgreSQL to be ready
wait_for_postgresql() {
    log "INFO" "Waiting for PostgreSQL to be ready..."
    local timeout=90
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
            log "SUCCESS" "PostgreSQL is ready and accepting connections"
            return 0
        fi
        
        # Check container status
        local status=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        if [[ "$status" != "running" ]]; then
            log "ERROR" "PostgreSQL container stopped running (status: $status)"
            docker logs "$CONTAINER_NAME" 2>/dev/null | tail -20 || true
            return 1
        fi
        
        sleep 3
        elapsed=$((elapsed + 3))
        log "INFO" "Waiting for PostgreSQL... (${elapsed}/${timeout}s)"
    done
    
    log "ERROR" "PostgreSQL failed to become ready within $timeout seconds"
    docker logs "$CONTAINER_NAME" 2>/dev/null | tail -30 || true
    return 1
}

# Test basic PostgreSQL operations
test_basic_operations() {
    log "INFO" "Testing basic PostgreSQL operations..."
    
    # Test connection
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log "SUCCESS" "Database connection successful"
    else
        log "ERROR" "Database connection failed"
        return 1
    fi
    
    # Test CREATE TABLE
    local test_table="independence_test_$(date +%s)"
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE TABLE $test_table (id SERIAL PRIMARY KEY, data TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" > /dev/null 2>&1; then
        log "SUCCESS" "CREATE TABLE operation successful"
    else
        log "ERROR" "CREATE TABLE operation failed"
        return 1
    fi
    
    # Test INSERT
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $test_table (data) VALUES ('test_data_123'), ('test_data_456');" > /dev/null 2>&1; then
        log "SUCCESS" "INSERT operation successful"
    else
        log "ERROR" "INSERT operation failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test SELECT
    local result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM $test_table;" 2>/dev/null | tr -d ' ')
    if [[ "$result" == "2" ]]; then
        log "SUCCESS" "SELECT operation successful (found $result rows)"
    else
        log "ERROR" "SELECT operation failed. Expected: 2, Got: $result"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test UPDATE
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "UPDATE $test_table SET data = 'updated_data' WHERE id = 1;" > /dev/null 2>&1; then
        log "SUCCESS" "UPDATE operation successful"
    else
        log "ERROR" "UPDATE operation failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Verify UPDATE
    local updated_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT data FROM $test_table WHERE id = 1;" 2>/dev/null | tr -d ' ')
    if [[ "$updated_result" == "updated_data" ]]; then
        log "SUCCESS" "UPDATE verification successful"
    else
        log "ERROR" "UPDATE verification failed. Expected: updated_data, Got: $updated_result"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test DELETE
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DELETE FROM $test_table WHERE id = 2;" > /dev/null 2>&1; then
        log "SUCCESS" "DELETE operation successful"
    else
        log "ERROR" "DELETE operation failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Verify DELETE
    local delete_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM $test_table;" 2>/dev/null | tr -d ' ')
    if [[ "$delete_result" == "1" ]]; then
        log "SUCCESS" "DELETE verification successful (remaining rows: $delete_result)"
    else
        log "ERROR" "DELETE verification failed. Expected: 1, Got: $delete_result"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test DROP TABLE
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1; then
        log "SUCCESS" "DROP TABLE operation successful"
    else
        log "ERROR" "DROP TABLE operation failed"
        return 1
    fi
    
    return 0
}

# Test advanced SQL features
test_advanced_features() {
    log "INFO" "Testing advanced PostgreSQL features..."
    
    local test_schema="independence_test_$(date +%s)"
    
    # Test schema creation
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE SCHEMA $test_schema;" > /dev/null 2>&1; then
        log "SUCCESS" "Schema creation successful"
    else
        log "ERROR" "Schema creation failed"
        return 1
    fi
    
    # Test table in schema
    local schema_table="${test_schema}.test_table"
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE TABLE $schema_table (id SERIAL, name VARCHAR(100), age INT);" > /dev/null 2>&1; then
        log "SUCCESS" "Table creation in schema successful"
    else
        log "ERROR" "Table creation in schema failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA $test_schema CASCADE;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test indexes
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE INDEX idx_${test_schema}_name ON $schema_table (name);" > /dev/null 2>&1; then
        log "SUCCESS" "Index creation successful"
    else
        log "ERROR" "Index creation failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA $test_schema CASCADE;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test functions
    local test_function="${test_schema}.test_function"
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE OR REPLACE FUNCTION $test_function(input_val INT) RETURNS INT AS \$\$ BEGIN RETURN input_val * 2; END; \$\$ LANGUAGE plpgsql;" > /dev/null 2>&1; then
        log "SUCCESS" "Function creation successful"
    else
        log "WARNING" "Function creation failed (plpgsql may not be available)"
    fi
    
    # Test function execution
    local function_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT ${test_function}(5);" 2>/dev/null | tr -d ' ' || echo "FAILED")
    if [[ "$function_result" == "10" ]]; then
        log "SUCCESS" "Function execution successful (5 * 2 = $function_result)"
    elif [[ "$function_result" == "FAILED" ]]; then
        log "WARNING" "Function execution failed (non-critical)"
    else
        log "WARNING" "Function execution returned unexpected result: $function_result"
    fi
    
    # Test transactions
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $schema_table (name, age) VALUES ('John', 30);" > /dev/null 2>&1
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "BEGIN; INSERT INTO $schema_table (name, age) VALUES ('Jane', 25); ROLLBACK;" > /dev/null 2>&1; then
        log "SUCCESS" "Transaction (BEGIN/ROLLBACK) successful"
    else
        log "ERROR" "Transaction test failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA $test_schema CASCADE;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Verify rollback worked
    local row_count=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM $schema_table;" 2>/dev/null | tr -d ' ')
    if [[ "$row_count" == "1" ]]; then
        log "SUCCESS" "Transaction rollback verification successful (rows: $row_count)"
    else
        log "ERROR" "Transaction rollback failed (expected 1 row, got $row_count)"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA $test_schema CASCADE;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Cleanup
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA $test_schema CASCADE;" > /dev/null 2>&1
    
    return 0
}

# Test data types
test_data_types() {
    log "INFO" "Testing PostgreSQL data types..."
    
    local test_table="data_types_test_$(date +%s)"
    
    # Create table with various data types
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE TABLE $test_table (
        id SERIAL PRIMARY KEY,
        text_col TEXT,
        varchar_col VARCHAR(50),
        int_col INTEGER,
        bigint_col BIGINT,
        decimal_col DECIMAL(10,2),
        bool_col BOOLEAN,
        date_col DATE,
        timestamp_col TIMESTAMP,
        json_col JSON,
        uuid_col UUID DEFAULT gen_random_uuid()
    );" > /dev/null 2>&1; then
        log "SUCCESS" "Data types table creation successful"
    else
        log "ERROR" "Data types table creation failed"
        return 1
    fi
    
    # Insert test data
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $test_table (text_col, varchar_col, int_col, bigint_col, decimal_col, bool_col, date_col, timestamp_col, json_col) VALUES (
        'Long text value for testing',
        'Short text',
        42,
        9223372036854775807,
        123.45,
        true,
        '2023-01-01',
        '2023-01-01 12:00:00',
        '{\"key\": \"value\", \"number\": 123}'
    );" > /dev/null 2>&1; then
        log "SUCCESS" "Data types INSERT successful"
    else
        log "ERROR" "Data types INSERT failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test JSON operations
    local json_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT json_col->>'key' FROM $test_table WHERE id = 1;" 2>/dev/null | tr -d ' ')
    if [[ "$json_result" == "value" ]]; then
        log "SUCCESS" "JSON operations working correctly"
    else
        log "WARNING" "JSON operations may not be working (result: $json_result)"
    fi
    
    # Test UUID generation
    local uuid_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT uuid_col FROM $test_table WHERE id = 1;" 2>/dev/null | tr -d ' ')
    if [[ ${#uuid_result} -eq 36 ]]; then
        log "SUCCESS" "UUID generation working (UUID: $uuid_result)"
    else
        log "WARNING" "UUID generation may not be working"
    fi
    
    # Test date/time operations
    local date_result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT date_col FROM $test_table WHERE id = 1;" 2>/dev/null | tr -d ' ')
    if [[ "$date_result" == "2023-01-01" ]]; then
        log "SUCCESS" "Date operations working correctly"
    else
        log "WARNING" "Date operations may not be working (result: $date_result)"
    fi
    
    # Cleanup
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1
    
    return 0
}

# Test performance
test_performance() {
    log "INFO" "Testing PostgreSQL performance..."
    
    local perf_table="performance_test_$(date +%s)"
    local test_rows=1000
    
    # Create performance test table
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE TABLE $perf_table (id SERIAL PRIMARY KEY, data TEXT, number INTEGER);" > /dev/null 2>&1
    
    # Measure INSERT performance
    local start_time=$(date +%s.%N)
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $perf_table (data, number) SELECT 'test_data_' || generate_series, generate_series FROM generate_series(1, $test_rows);" > /dev/null 2>&1
    local insert_end_time=$(date +%s.%N)
    local insert_duration=$(echo "$insert_end_time - $start_time" | bc -l)
    local insert_rate=$(echo "scale=2; $test_rows / $insert_duration" | bc -l)
    
    log "SUCCESS" "INSERT performance: ${insert_rate} rows/sec ($test_rows rows in ${insert_duration}s)"
    
    # Measure SELECT performance
    start_time=$(date +%s.%N)
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM $perf_table;" > /dev/null 2>&1
    local select_end_time=$(date +%s.%N)
    local select_duration=$(echo "$select_end_time - $start_time" | bc -l)
    
    log "SUCCESS" "SELECT performance: ${select_duration}s for COUNT($test_rows rows)"
    
    # Test with index
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE INDEX idx_${perf_table}_number ON $perf_table (number);" > /dev/null 2>&1
    
    start_time=$(date +%s.%N)
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT * FROM $perf_table WHERE number = 500;" > /dev/null 2>&1
    local indexed_select_end_time=$(date +%s.%N)
    local indexed_select_duration=$(echo "$indexed_select_end_time - $start_time" | bc -l)
    
    log "SUCCESS" "Indexed SELECT performance: ${indexed_select_duration}s for single row lookup"
    
    # Cleanup
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $perf_table;" > /dev/null 2>&1
    
    # Check if performance is acceptable
    if (( $(echo "$insert_rate > 100" | bc -l) )); then
        log "SUCCESS" "Insert performance is acceptable (>100 rows/sec)"
    else
        log "WARNING" "Insert performance may be suboptimal (<100 rows/sec)"
    fi
    
    if (( $(echo "$select_duration < 1" | bc -l) )); then
        log "SUCCESS" "Select performance is acceptable (<1s for COUNT)"
    else
        log "WARNING" "Select performance may be suboptimal (>1s for COUNT)"
    fi
    
    return 0
}

# Test backup and restore capabilities
test_backup_restore() {
    log "INFO" "Testing PostgreSQL backup and restore capabilities..."
    
    local test_table="backup_test_$(date +%s)"
    local backup_file="/tmp/backup_test.sql"
    
    # Create test data
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE TABLE $test_table (id SERIAL PRIMARY KEY, data TEXT);" > /dev/null 2>&1
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "INSERT INTO $test_table (data) VALUES ('backup_test_data_1'), ('backup_test_data_2');" > /dev/null 2>&1
    
    # Test pg_dump
    if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" -t "$test_table" > /dev/null 2>&1; then
        log "SUCCESS" "pg_dump command successful"
    else
        log "ERROR" "pg_dump command failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Create backup to file
    if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" -t "$test_table" -f "$backup_file" > /dev/null 2>&1; then
        log "SUCCESS" "Backup to file successful"
    else
        log "ERROR" "Backup to file failed"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Verify backup file exists and has content
    local backup_size=$(docker exec "$CONTAINER_NAME" stat -c%s "$backup_file" 2>/dev/null || echo "0")
    if [[ "$backup_size" -gt 0 ]]; then
        log "SUCCESS" "Backup file created with size: ${backup_size} bytes"
    else
        log "ERROR" "Backup file is empty or does not exist"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        return 1
    fi
    
    # Test restore by dropping and recreating table
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1
    
    if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f "$backup_file" > /dev/null 2>&1; then
        log "SUCCESS" "Restore from backup successful"
    else
        log "ERROR" "Restore from backup failed"
        docker exec "$CONTAINER_NAME" rm -f "$backup_file" 2>/dev/null || true
        return 1
    fi
    
    # Verify restored data
    local restored_count=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM $test_table;" 2>/dev/null | tr -d ' ')
    if [[ "$restored_count" == "2" ]]; then
        log "SUCCESS" "Backup/restore verification successful (restored $restored_count rows)"
    else
        log "ERROR" "Backup/restore verification failed (expected 2 rows, got $restored_count)"
        docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1 || true
        docker exec "$CONTAINER_NAME" rm -f "$backup_file" 2>/dev/null || true
        return 1
    fi
    
    # Cleanup
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "DROP TABLE $test_table;" > /dev/null 2>&1
    docker exec "$CONTAINER_NAME" rm -f "$backup_file" 2>/dev/null || true
    
    return 0
}

# Test resource usage
test_resource_usage() {
    log "INFO" "Testing PostgreSQL resource usage..."
    
    # Get container stats
    local stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" "$CONTAINER_NAME" 2>/dev/null || echo "FAILED")
    
    if [[ "$stats" != "FAILED" ]]; then
        log "INFO" "PostgreSQL container resource usage:"
        echo "$stats"
        
        # Extract CPU percentage
        local cpu_percent=$(echo "$stats" | tail -n 1 | awk '{print $1}' | sed 's/%//')
        if [[ -n "$cpu_percent" && "$cpu_percent" != "--" ]]; then
            if (( $(echo "$cpu_percent < 20" | bc -l 2>/dev/null || echo 0) )); then
                log "SUCCESS" "CPU usage is normal ($cpu_percent%)"
            else
                log "WARNING" "CPU usage is elevated ($cpu_percent%)"
            fi
        fi
        
        # Extract memory usage
        local mem_usage=$(echo "$stats" | tail -n 1 | awk '{print $2}' | sed 's/MiB.*//')
        if [[ -n "$mem_usage" && "$mem_usage" != "--" ]]; then
            if (( $(echo "$mem_usage < 500" | bc -l 2>/dev/null || echo 0) )); then
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

# Test connection limits
test_connection_limits() {
    log "INFO" "Testing PostgreSQL connection limits..."
    
    # Check current connections
    local current_connections=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')
    if [[ -n "$current_connections" && "$current_connections" -gt 0 ]]; then
        log "SUCCESS" "Connection count query successful (current connections: $current_connections)"
    else
        log "ERROR" "Connection count query failed"
        return 1
    fi
    
    # Check max connections setting
    local max_connections=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SHOW max_connections;" 2>/dev/null | tr -d ' ')
    if [[ -n "$max_connections" && "$max_connections" -gt 0 ]]; then
        log "SUCCESS" "Max connections setting accessible (max: $max_connections)"
    else
        log "ERROR" "Max connections setting query failed"
        return 1
    fi
    
    # Test multiple connections (simple test with 5 connections)
    local connection_test_results=()
    for i in {1..5}; do
        if docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT $i;" > /dev/null 2>&1; then
            connection_test_results+=("$i:SUCCESS")
        else
            connection_test_results+=("$i:FAILED")
        fi
    done
    
    local successful_connections=$(echo "${connection_test_results[@]}" | grep -o "SUCCESS" | wc -l)
    if [[ "$successful_connections" -eq 5 ]]; then
        log "SUCCESS" "Multiple connection test successful (5/5 connections)"
    else
        log "WARNING" "Multiple connection test partial success ($successful_connections/5 connections)"
    fi
    
    return 0
}

# Main test function
run_postgresql_test() {
    local test_results=()
    
    log "INFO" "Starting PostgreSQL service independence test..."
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    # Start PostgreSQL service
    if ! start_postgresql_service; then
        log "ERROR" "Failed to start PostgreSQL service"
        return 1
    fi
    
    # Wait for service to be ready
    if ! wait_for_postgresql; then
        log "ERROR" "PostgreSQL service failed to become ready"
        return 1
    fi
    
    # Run tests
    log "INFO" "Running comprehensive PostgreSQL service tests..."
    
    # Test basic operations
    if test_basic_operations; then
        test_results+=("basic_operations:PASS")
    else
        test_results+=("basic_operations:FAIL")
    fi
    
    # Test advanced features
    if test_advanced_features; then
        test_results+=("advanced_features:PASS")
    else
        test_results+=("advanced_features:FAIL")
    fi
    
    # Test data types
    if test_data_types; then
        test_results+=("data_types:PASS")
    else
        test_results+=("data_types:FAIL")
    fi
    
    # Test performance
    if test_performance; then
        test_results+=("performance:PASS")
    else
        test_results+=("performance:FAIL")
    fi
    
    # Test backup and restore
    if test_backup_restore; then
        test_results+=("backup_restore:PASS")
    else
        test_results+=("backup_restore:FAIL")
    fi
    
    # Test resource usage
    if test_resource_usage; then
        test_results+=("resource_usage:PASS")
    else
        test_results+=("resource_usage:FAIL")
    fi
    
    # Test connection limits
    if test_connection_limits; then
        test_results+=("connection_limits:PASS")
    else
        test_results+=("connection_limits:FAIL")
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
        log "SUCCESS" "All PostgreSQL service tests passed!"
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

Test PostgreSQL service for independence and functionality.

OPTIONS:
    --help              Show this help message

EXAMPLES:
    $0                  # Run PostgreSQL independence test

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
    
    if run_postgresql_test; then
        echo -e "\n${GREEN}✅ PostgreSQL service independence test completed successfully${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ PostgreSQL service independence test failed${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"