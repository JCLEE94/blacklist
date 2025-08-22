#!/bin/bash

# Docker Independence Test Orchestrator
# Version: v1.0.37
# Purpose: Orchestrate all Docker service independence tests with comprehensive reporting

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/independence-tests"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ORCHESTRATOR_LOG="$LOG_DIR/orchestrator_$TIMESTAMP.log"

# Test configuration
PARALLEL_TESTS=false
GENERATE_REPORT=true
CLEANUP_AFTER_TESTS=true
TIMEOUT_PER_TEST=600  # 10 minutes per test

# Service test scripts
declare -A TEST_SCRIPTS=(
    ["blacklist"]="$SCRIPT_DIR/test-blacklist-service.sh"
    ["redis"]="$SCRIPT_DIR/test-redis-service.sh"
    ["postgresql"]="$SCRIPT_DIR/test-postgresql-service.sh"
    ["monitoring"]="$SCRIPT_DIR/test-monitoring-services.sh"
    ["comprehensive"]="$SCRIPT_DIR/test-docker-independence.sh"
)

# Service categories
declare -A SERVICE_CATEGORIES=(
    ["core"]="blacklist redis postgresql"
    ["monitoring"]="monitoring"
    ["all"]="blacklist redis postgresql monitoring"
    ["comprehensive"]="comprehensive"
)

# Test results tracking
declare -A TEST_RESULTS=()
declare -A TEST_DURATIONS=()
declare -A TEST_LOGS=()

# Initialize logging
initialize_logging() {
    mkdir -p "$LOG_DIR"
    touch "$ORCHESTRATOR_LOG"
    echo "=== Docker Independence Test Orchestrator - $TIMESTAMP ===" > "$ORCHESTRATOR_LOG"
    echo "Test started at: $(date)" >> "$ORCHESTRATOR_LOG"
    echo "" >> "$ORCHESTRATOR_LOG"
}

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$ORCHESTRATOR_LOG"
    
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
        "HEADER")
            echo -e "${PURPLE}[TEST]${NC} $message"
            ;;
        "RESULT")
            echo -e "${CYAN}[RESULT]${NC} $message"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking orchestrator prerequisites..."
    
    # Check if test scripts exist
    for service in "${!TEST_SCRIPTS[@]}"; do
        local script="${TEST_SCRIPTS[$service]}"
        if [[ ! -f "$script" ]]; then
            log "ERROR" "Test script not found: $script"
            return 1
        fi
        
        if [[ ! -x "$script" ]]; then
            log "INFO" "Making test script executable: $script"
            chmod +x "$script" || {
                log "ERROR" "Failed to make script executable: $script"
                return 1
            }
        fi
    done
    
    # Check Docker prerequisites
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is not installed"
        return 1
    fi
    
    if ! command -v timeout &> /dev/null; then
        log "ERROR" "timeout command is not available"
        return 1
    fi
    
    # Check disk space
    local available_space=$(df "$LOG_DIR" --output=avail | tail -1)
    if [[ $available_space -lt 1048576 ]]; then  # Less than 1GB
        log "WARNING" "Low disk space available for logs: ${available_space}KB"
    fi
    
    log "SUCCESS" "All prerequisites met"
    return 0
}

# Clean up function
cleanup() {
    log "INFO" "Performing orchestrator cleanup..."
    cd "$PROJECT_DIR"
    
    # Stop all services
    docker-compose down --remove-orphans 2>/dev/null || true
    docker-compose --profile watchtower --profile monitoring down --remove-orphans 2>/dev/null || true
    
    # Remove test containers if they exist
    docker ps -a --format "table {{.Names}}" | grep -E "test-|independence-" | xargs -r docker rm -f 2>/dev/null || true
    
    # Kill any running test processes
    pkill -f "test-.*-service.sh" 2>/dev/null || true
    
    log "INFO" "Orchestrator cleanup completed"
}

# Run single test with timeout
run_single_test() {
    local service=$1
    local test_script="${TEST_SCRIPTS[$service]}"
    local test_args="${2:-}"
    
    log "HEADER" "Starting $service independence test..."
    
    local test_log="$LOG_DIR/${service}_test_$TIMESTAMP.log"
    local start_time=$(date +%s)
    local result="UNKNOWN"
    
    # Run test with timeout
    if timeout $TIMEOUT_PER_TEST bash "$test_script" $test_args > "$test_log" 2>&1; then
        result="PASS"
        log "SUCCESS" "$service test completed successfully"
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            result="TIMEOUT"
            log "ERROR" "$service test timed out after ${TIMEOUT_PER_TEST}s"
        else
            result="FAIL"
            log "ERROR" "$service test failed with exit code: $exit_code"
        fi
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Store results
    TEST_RESULTS["$service"]="$result"
    TEST_DURATIONS["$service"]="$duration"
    TEST_LOGS["$service"]="$test_log"
    
    log "RESULT" "$service: $result (${duration}s)"
    
    return 0
}

# Run tests in parallel
run_parallel_tests() {
    local services=($1)
    local pids=()
    
    log "INFO" "Running tests in parallel for: ${services[*]}"
    
    # Start all tests
    for service in "${services[@]}"; do
        (
            run_single_test "$service"
        ) &
        pids+=($!)
        log "INFO" "Started $service test in background (PID: $!)"
    done
    
    # Wait for all tests to complete
    local completed=0
    local total=${#pids[@]}
    
    for pid in "${pids[@]}"; do
        if wait $pid; then
            ((completed++))
            log "INFO" "Background test completed ($completed/$total)"
        else
            log "WARNING" "Background test failed (PID: $pid)"
        fi
    done
    
    log "INFO" "Parallel test execution completed ($completed/$total tests finished)"
    return 0
}

# Run tests sequentially
run_sequential_tests() {
    local services=($1)
    
    log "INFO" "Running tests sequentially for: ${services[*]}"
    
    for service in "${services[@]}"; do
        run_single_test "$service"
        
        # Cleanup between tests
        if [[ "$CLEANUP_AFTER_TESTS" == "true" ]]; then
            log "INFO" "Cleaning up after $service test..."
            cleanup
            sleep 5
        fi
    done
    
    log "INFO" "Sequential test execution completed"
    return 0
}

# Generate comprehensive report
generate_report() {
    log "INFO" "Generating comprehensive test report..."
    
    local report_file="$LOG_DIR/independence_report_$TIMESTAMP.html"
    local summary_file="$LOG_DIR/independence_summary_$TIMESTAMP.txt"
    
    # Generate HTML report
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docker Independence Test Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { background: #ecf0f1; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .test-result { margin: 15px 0; padding: 15px; border-radius: 8px; }
        .pass { background: #d5f4e6; border-left: 5px solid #27ae60; }
        .fail { background: #fadbd8; border-left: 5px solid #e74c3c; }
        .timeout { background: #fdf2e9; border-left: 5px solid #f39c12; }
        .unknown { background: #eaecee; border-left: 5px solid #95a5a6; }
        .metric { display: inline-block; margin: 10px 20px 10px 0; }
        .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-label { font-size: 14px; color: #7f8c8d; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; }
        tr:nth-child(even) { background-color: #f8f9fa; }
        .log-link { color: #3498db; text-decoration: none; }
        .log-link:hover { text-decoration: underline; }
        .timestamp { color: #7f8c8d; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐳 Docker Independence Test Report</h1>
        <div class="timestamp">Generated on: $(date)</div>
        
        <div class="summary">
            <h2>📊 Test Summary</h2>
EOF
    
    # Calculate summary statistics
    local total_tests=${#TEST_RESULTS[@]}
    local passed_tests=0
    local failed_tests=0
    local timeout_tests=0
    local unknown_tests=0
    local total_duration=0
    
    for service in "${!TEST_RESULTS[@]}"; do
        case "${TEST_RESULTS[$service]}" in
            "PASS") ((passed_tests++)) ;;
            "FAIL") ((failed_tests++)) ;;
            "TIMEOUT") ((timeout_tests++)) ;;
            "UNKNOWN") ((unknown_tests++)) ;;
        esac
        total_duration=$((total_duration + ${TEST_DURATIONS[$service]}))
    done
    
    # Add summary to HTML
    cat >> "$report_file" << EOF
            <div class="metric">
                <div class="metric-value">$total_tests</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #27ae60;">$passed_tests</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #e74c3c;">$failed_tests</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value" style="color: #f39c12;">$timeout_tests</div>
                <div class="metric-label">Timeout</div>
            </div>
            <div class="metric">
                <div class="metric-value">$((total_duration / 60))m $((total_duration % 60))s</div>
                <div class="metric-label">Total Duration</div>
            </div>
        </div>
        
        <h2>🔍 Test Results</h2>
        <table>
            <tr>
                <th>Service</th>
                <th>Result</th>
                <th>Duration</th>
                <th>Log File</th>
            </tr>
EOF
    
    # Add test results to HTML
    for service in "${!TEST_RESULTS[@]}"; do
        local result="${TEST_RESULTS[$service]}"
        local duration="${TEST_DURATIONS[$service]}"
        local log_file="${TEST_LOGS[$service]}"
        local log_basename=$(basename "$log_file")
        
        local result_class
        case "$result" in
            "PASS") result_class="pass" ;;
            "FAIL") result_class="fail" ;;
            "TIMEOUT") result_class="timeout" ;;
            *) result_class="unknown" ;;
        esac
        
        cat >> "$report_file" << EOF
            <tr>
                <td><strong>$service</strong></td>
                <td><span class="test-result $result_class" style="padding: 5px 10px; display: inline-block;">$result</span></td>
                <td>${duration}s</td>
                <td><a href="$log_basename" class="log-link">$log_basename</a></td>
            </tr>
EOF
    done
    
    # Close HTML
    cat >> "$report_file" << 'EOF'
        </table>
        
        <h2>📝 Test Details</h2>
        <p>Each test validates the independence and functionality of Docker services:</p>
        <ul>
            <li><strong>Blacklist Service:</strong> Main application with health checks, API endpoints, database/cache connectivity</li>
            <li><strong>Redis Service:</strong> Cache operations, data types, TTL, persistence, performance</li>
            <li><strong>PostgreSQL Service:</strong> CRUD operations, advanced features, data types, backup/restore</li>
            <li><strong>Monitoring Services:</strong> Watchtower, Prometheus, Grafana functionality and integration</li>
        </ul>
        
        <h2>🚀 Next Steps</h2>
        <p>Review failed tests and check individual log files for detailed error information. Each service should be capable of independent operation for proper microservices architecture.</p>
    </div>
</body>
</html>
EOF
    
    # Generate text summary
    cat > "$summary_file" << EOF
Docker Independence Test Summary - $TIMESTAMP
==========================================

Test Overview:
- Total Tests: $total_tests
- Passed: $passed_tests
- Failed: $failed_tests
- Timeout: $timeout_tests
- Unknown: $unknown_tests
- Total Duration: $((total_duration / 60))m $((total_duration % 60))s

Test Results:
EOF
    
    for service in "${!TEST_RESULTS[@]}"; do
        printf "%-15s: %-8s (%3ds)\n" "$service" "${TEST_RESULTS[$service]}" "${TEST_DURATIONS[$service]}" >> "$summary_file"
    done
    
    cat >> "$summary_file" << EOF

Test Success Rate: $(echo "scale=1; $passed_tests * 100 / $total_tests" | bc -l)%

Log Files:
EOF
    
    for service in "${!TEST_LOGS[@]}"; do
        echo "- $service: ${TEST_LOGS[$service]}" >> "$summary_file"
    done
    
    log "SUCCESS" "Report generated:"
    log "INFO" "HTML Report: $report_file"
    log "INFO" "Summary: $summary_file"
    
    # Display summary
    echo -e "\n${CYAN}=== Test Summary ===${NC}"
    cat "$summary_file"
}

# Main orchestration function
run_orchestrated_tests() {
    local test_category=${1:-"all"}
    local services_to_test
    
    # Determine services to test
    if [[ -n "${SERVICE_CATEGORIES[$test_category]:-}" ]]; then
        services_to_test="${SERVICE_CATEGORIES[$test_category]}"
    elif [[ -n "${TEST_SCRIPTS[$test_category]:-}" ]]; then
        services_to_test="$test_category"
    else
        log "ERROR" "Unknown test category or service: $test_category"
        return 1
    fi
    
    log "INFO" "Orchestrating tests for: $services_to_test"
    
    # Convert to array
    local services_array=($services_to_test)
    
    # Run tests
    if [[ "$PARALLEL_TESTS" == "true" ]]; then
        run_parallel_tests "$services_to_test"
    else
        run_sequential_tests "$services_to_test"
    fi
    
    # Generate report
    if [[ "$GENERATE_REPORT" == "true" ]]; then
        generate_report
    fi
    
    # Calculate final result
    local total_tests=${#TEST_RESULTS[@]}
    local failed_count=0
    
    for service in "${!TEST_RESULTS[@]}"; do
        if [[ "${TEST_RESULTS[$service]}" != "PASS" ]]; then
            ((failed_count++))
        fi
    done
    
    log "INFO" "Orchestration completed: $((total_tests - failed_count))/$total_tests tests passed"
    
    if [[ $failed_count -eq 0 ]]; then
        echo -e "\n${GREEN}✅ All Docker services passed independence tests!${NC}"
        echo -e "${GREEN}Services are properly independent and functional.${NC}"
        return 0
    else
        echo -e "\n${RED}❌ $failed_count out of $total_tests services failed independence tests${NC}"
        echo -e "${RED}Check individual test logs for details.${NC}"
        return 1
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [CATEGORY]

Orchestrate Docker service independence tests with comprehensive reporting.

OPTIONS:
    --parallel          Run tests in parallel (default: sequential)
    --no-report         Skip report generation
    --no-cleanup        Skip cleanup after tests
    --timeout SECONDS   Set timeout per test (default: $TIMEOUT_PER_TEST)
    --help              Show this help message

CATEGORIES:
    core                Test core services (blacklist, redis, postgresql)
    monitoring          Test monitoring services (watchtower, prometheus, grafana)
    all                 Test all individual services (default)
    comprehensive       Run comprehensive test suite
    SERVICE_NAME        Test specific service only

SERVICES:
    blacklist           Main application service
    redis               Cache service
    postgresql          Database service
    monitoring          All monitoring services

EXAMPLES:
    $0                           # Test all services sequentially
    $0 --parallel core           # Test core services in parallel
    $0 --no-report blacklist     # Test blacklist only, no report
    $0 comprehensive             # Run comprehensive test suite

REPORTS:
    - HTML report with detailed results and metrics
    - Text summary with pass/fail status
    - Individual service logs for debugging
    - All reports saved to: $LOG_DIR

EOF
}

# Main execution
main() {
    local test_category="all"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --parallel)
                PARALLEL_TESTS=true
                shift
                ;;
            --no-report)
                GENERATE_REPORT=false
                shift
                ;;
            --no-cleanup)
                CLEANUP_AFTER_TESTS=false
                shift
                ;;
            --timeout)
                TIMEOUT_PER_TEST="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            core|monitoring|all|comprehensive|blacklist|redis|postgresql)
                test_category="$1"
                shift
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Initialize
    initialize_logging
    
    echo -e "${PURPLE}🐳 Docker Independence Test Orchestrator${NC}"
    echo -e "${BLUE}Testing category: $test_category${NC}"
    echo -e "${BLUE}Parallel execution: $PARALLEL_TESTS${NC}"
    echo -e "${BLUE}Generate report: $GENERATE_REPORT${NC}"
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Set trap for cleanup on exit
    if [[ "$CLEANUP_AFTER_TESTS" == "true" ]]; then
        trap cleanup EXIT
    fi
    
    # Run orchestrated tests
    if run_orchestrated_tests "$test_category"; then
        log "SUCCESS" "Docker independence test orchestration completed successfully"
        exit 0
    else
        log "ERROR" "Docker independence test orchestration failed"
        exit 1
    fi
}

# Execute main function
main "$@"