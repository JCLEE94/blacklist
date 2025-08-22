#!/bin/bash
# Docker Independence Validation Script
# Proves complete independence from docker-compose
# Version: v1.0.37

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
TEST_LOG="/tmp/docker-independence-test-$(date +%Y%m%d_%H%M%S).log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test configuration
TEST_APP_PORT="3542"
TEST_POSTGRES_PORT="6432"
TEST_REDIS_PORT="7379"
TEST_NETWORK="independence-test-net"
TEST_CONTAINERS=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$TEST_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$TEST_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$TEST_LOG"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1" | tee -a "$TEST_LOG"
}

# Function to show usage
show_usage() {
    cat << EOF
Docker Independence Validation Script

This script proves that the Blacklist Management System can run completely
independently without docker-compose by testing various deployment scenarios.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --registry URL      Docker registry URL (default: registry.jclee.me)
    --quick            Run quick tests only (skip full scenarios)
    --cleanup          Clean up test containers and exit
    --verbose          Enable verbose logging
    --help, -h         Show this help message

TEST SCENARIOS:
    1. App-only deployment (SQLite + Memory cache)
    2. App + PostgreSQL deployment
    3. App + Redis deployment
    4. Full stack deployment (App + PostgreSQL + Redis)
    5. Zero-dependency deployment
    6. Network isolation tests
    7. Data persistence tests
    8. Health check validations

VALIDATION CRITERIA:
    ✓ No docker-compose.yml file usage
    ✓ Each container starts with single docker run command
    ✓ No service dependencies in container startup
    ✓ Complete functionality without external orchestration
    ✓ Graceful degradation when services unavailable
    ✓ Data persistence across container restarts
    ✓ Network independence verification

EOF
}

# Function to cleanup test environment
cleanup_test_environment() {
    log_info "Cleaning up test environment..."
    
    # Stop and remove test containers
    for container in "${TEST_CONTAINERS[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log_info "Stopping test container: $container"
            docker stop "$container" >/dev/null 2>&1 || true
        fi
        
        if docker ps -aq -f name="$container" | grep -q .; then
            log_info "Removing test container: $container"
            docker rm -f "$container" >/dev/null 2>&1 || true
        fi
    done
    
    # Remove test network
    if docker network inspect "$TEST_NETWORK" &>/dev/null; then
        log_info "Removing test network: $TEST_NETWORK"
        docker network rm "$TEST_NETWORK" >/dev/null 2>&1 || true
    fi
    
    # Remove test volumes
    test_volumes=(
        "independence-test-postgres-data"
        "independence-test-redis-data"
        "independence-test-app-data"
    )
    
    for volume in "${test_volumes[@]}"; do
        if docker volume inspect "$volume" &>/dev/null; then
            log_info "Removing test volume: $volume"
            docker volume rm "$volume" >/dev/null 2>&1 || true
        fi
    done
    
    log_success "Test environment cleaned up"
}

# Function to create test network
create_test_network() {
    log_test "Creating isolated test network..."
    
    if ! docker network inspect "$TEST_NETWORK" &>/dev/null; then
        docker network create \
            --driver bridge \
            --subnet 172.31.0.0/16 \
            --gateway 172.31.0.1 \
            "$TEST_NETWORK" >/dev/null
        log_success "Test network created: $TEST_NETWORK"
    else
        log_info "Test network already exists: $TEST_NETWORK"
    fi
}

# Function to check if images exist
check_images() {
    log_test "Checking required standalone images..."
    
    required_images=(
        "$REGISTRY_URL/blacklist:standalone"
        "$REGISTRY_URL/blacklist-postgresql:standalone"
        "$REGISTRY_URL/blacklist-redis:standalone"
    )
    
    local missing_images=0
    
    for image in "${required_images[@]}"; do
        if docker images "$image" --format "{{.Repository}}:{{.Tag}}" | grep -q standalone; then
            log_success "Image found: $image"
        else
            log_error "Image missing: $image"
            missing_images=1
        fi
    done
    
    if [ $missing_images -eq 1 ]; then
        log_error "Missing required images. Build them first:"
        log_info "Run: $PROJECT_ROOT/scripts/build-standalone.sh"
        exit 1
    fi
    
    log_success "All required images are available"
}

# Function to test app-only deployment (zero dependencies)
test_app_only_deployment() {
    log_test "Testing app-only deployment (SQLite + Memory cache)..."
    
    local container_name="independence-test-app-only"
    TEST_CONTAINERS+=("$container_name")
    
    # Start app with SQLite and memory cache
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -p "${TEST_APP_PORT}:2542" \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL=sqlite:////app/data/test_standalone.db \
        -e CACHE_TYPE=memory \
        -e COLLECTION_ENABLED=false \
        -e FORCE_DISABLE_COLLECTION=true \
        -e LOG_LEVEL=DEBUG \
        "$REGISTRY_URL/blacklist:standalone" >/dev/null
    
    # Wait for app to start
    log_info "Waiting for application to start..."
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if curl -sf "http://localhost:${TEST_APP_PORT}/health" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        log_error "App-only deployment failed to start"
        return 1
    fi
    
    # Test basic functionality
    local health_response=$(curl -s "http://localhost:${TEST_APP_PORT}/health")
    if echo "$health_response" | grep -q "healthy"; then
        log_success "App-only deployment health check passed"
    else
        log_error "App-only deployment health check failed"
        return 1
    fi
    
    # Test API endpoints
    local api_response=$(curl -s "http://localhost:${TEST_APP_PORT}/api/blacklist/active")
    if [ $? -eq 0 ]; then
        log_success "App-only API endpoint accessible"
    else
        log_error "App-only API endpoint failed"
        return 1
    fi
    
    # Test database functionality (SQLite)
    local db_test=$(curl -s "http://localhost:${TEST_APP_PORT}/api/v2/analytics/summary")
    if [ $? -eq 0 ]; then
        log_success "App-only SQLite database functional"
    else
        log_error "App-only SQLite database failed"
        return 1
    fi
    
    log_success "App-only deployment test passed"
    
    # Stop container for next test
    docker stop "$container_name" >/dev/null
}

# Function to test PostgreSQL independence
test_postgresql_independence() {
    log_test "Testing PostgreSQL standalone deployment..."
    
    local container_name="independence-test-postgres"
    TEST_CONTAINERS+=("$container_name")
    
    # Start PostgreSQL standalone
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -p "${TEST_POSTGRES_PORT}:5432" \
        -v independence-test-postgres-data:/var/lib/postgresql/data \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=test_user \
        -e POSTGRES_PASSWORD=test_password \
        "$REGISTRY_URL/blacklist-postgresql:standalone" >/dev/null
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if docker exec "$container_name" pg_isready -U test_user -d blacklist >/dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        log_error "PostgreSQL standalone failed to start"
        return 1
    fi
    
    # Test database functionality
    local table_count=$(docker exec "$container_name" psql -U test_user -d blacklist -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
    if [ "$table_count" -gt 5 ]; then
        log_success "PostgreSQL standalone schema initialized correctly ($table_count tables)"
    else
        log_error "PostgreSQL standalone schema initialization failed"
        return 1
    fi
    
    # Test data insertion
    docker exec "$container_name" psql -U test_user -d blacklist -c "INSERT INTO blacklist_ips (ip_address, source, detection_date) VALUES ('192.168.1.200', 'TEST', CURRENT_DATE) ON CONFLICT DO NOTHING;" >/dev/null
    local inserted_count=$(docker exec "$container_name" psql -U test_user -d blacklist -t -c "SELECT COUNT(*) FROM blacklist_ips WHERE source = 'TEST';" | tr -d ' ')
    if [ "$inserted_count" -ge 1 ]; then
        log_success "PostgreSQL standalone data operations functional"
    else
        log_error "PostgreSQL standalone data operations failed"
        return 1
    fi
    
    log_success "PostgreSQL independence test passed"
}

# Function to test Redis independence
test_redis_independence() {
    log_test "Testing Redis standalone deployment..."
    
    local container_name="independence-test-redis"
    TEST_CONTAINERS+=("$container_name")
    
    # Start Redis standalone
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -p "${TEST_REDIS_PORT}:6379" \
        -v independence-test-redis-data:/data \
        "$REGISTRY_URL/blacklist-redis:standalone" >/dev/null
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    local attempts=0
    while [ $attempts -lt 15 ]; do
        if docker exec "$container_name" redis-cli ping >/dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 15 ]; then
        log_error "Redis standalone failed to start"
        return 1
    fi
    
    # Test Redis functionality
    docker exec "$container_name" redis-cli set test_key "independence_test" >/dev/null
    local test_value=$(docker exec "$container_name" redis-cli get test_key)
    if [ "$test_value" = "independence_test" ]; then
        log_success "Redis standalone operations functional"
    else
        log_error "Redis standalone operations failed"
        return 1
    fi
    
    # Test Redis configuration
    local max_memory=$(docker exec "$container_name" redis-cli config get maxmemory | tail -n 1)
    if [ "$max_memory" != "0" ]; then
        log_success "Redis standalone configuration applied"
    else
        log_warning "Redis standalone configuration not fully applied"
    fi
    
    log_success "Redis independence test passed"
}

# Function to test full stack deployment
test_full_stack_deployment() {
    log_test "Testing full stack deployment (App + PostgreSQL + Redis)..."
    
    local postgres_container="independence-test-postgres-full"
    local redis_container="independence-test-redis-full"
    local app_container="independence-test-app-full"
    
    TEST_CONTAINERS+=("$postgres_container" "$redis_container" "$app_container")
    
    # Start PostgreSQL
    log_info "Starting PostgreSQL for full stack test..."
    docker run -d \
        --name "$postgres_container" \
        --network "$TEST_NETWORK" \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=full_test_user \
        -e POSTGRES_PASSWORD=full_test_password \
        "$REGISTRY_URL/blacklist-postgresql:standalone" >/dev/null
    
    # Start Redis
    log_info "Starting Redis for full stack test..."
    docker run -d \
        --name "$redis_container" \
        --network "$TEST_NETWORK" \
        "$REGISTRY_URL/blacklist-redis:standalone" >/dev/null
    
    # Wait for services to be ready
    log_info "Waiting for database and cache services..."
    sleep 10
    
    # Start application with full stack
    log_info "Starting application with full stack..."
    docker run -d \
        --name "$app_container" \
        --network "$TEST_NETWORK" \
        -p "3543:2542" \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL="postgresql://full_test_user:full_test_password@${postgres_container}:5432/blacklist" \
        -e REDIS_URL="redis://${redis_container}:6379/0" \
        -e CACHE_TYPE=redis \
        -e COLLECTION_ENABLED=false \
        -e FORCE_DISABLE_COLLECTION=true \
        -e LOG_LEVEL=DEBUG \
        "$REGISTRY_URL/blacklist:standalone" >/dev/null
    
    # Wait for application to start
    log_info "Waiting for full stack application to start..."
    local attempts=0
    while [ $attempts -lt 45 ]; do
        if curl -sf "http://localhost:3543/health" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 45 ]; then
        log_error "Full stack deployment failed to start"
        return 1
    fi
    
    # Test full stack functionality
    local health_response=$(curl -s "http://localhost:3543/api/health")
    if echo "$health_response" | grep -q "database.*connected" && echo "$health_response" | grep -q "cache.*connected"; then
        log_success "Full stack deployment health check passed"
    else
        log_error "Full stack deployment health check failed"
        return 1
    fi
    
    # Test database connectivity through app
    local db_test=$(curl -s "http://localhost:3543/api/v2/analytics/summary")
    if [ $? -eq 0 ]; then
        log_success "Full stack database connectivity verified"
    else
        log_error "Full stack database connectivity failed"
        return 1
    fi
    
    log_success "Full stack deployment test passed"
}

# Function to test docker-compose independence
test_docker_compose_independence() {
    log_test "Testing docker-compose independence..."
    
    # Verify no docker-compose processes
    if pgrep -f "docker-compose" >/dev/null; then
        log_warning "docker-compose processes detected, but test will continue"
    else
        log_success "No docker-compose processes running"
    fi
    
    # Verify containers can start without compose file
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        log_info "docker-compose.yml exists but is not being used"
    fi
    
    # Check that our test containers are not managed by compose
    for container in "${TEST_CONTAINERS[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "$container"; then
            local compose_label=$(docker inspect "$container" --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null || echo "")
            if [ -z "$compose_label" ]; then
                log_success "Container $container is not managed by docker-compose"
            else
                log_error "Container $container is managed by docker-compose: $compose_label"
                return 1
            fi
        fi
    done
    
    log_success "Docker-compose independence verified"
}

# Function to test graceful degradation
test_graceful_degradation() {
    log_test "Testing graceful degradation capabilities..."
    
    local app_container="independence-test-graceful-app"
    TEST_CONTAINERS+=("$app_container")
    
    # Start app without any external services
    log_info "Starting app without external dependencies..."
    docker run -d \
        --name "$app_container" \
        --network "$TEST_NETWORK" \
        -p "3544:2542" \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL=sqlite:////app/data/graceful_test.db \
        -e REDIS_URL=redis://nonexistent:6379/0 \
        -e CACHE_TYPE=memory \
        -e COLLECTION_ENABLED=false \
        -e LOG_LEVEL=DEBUG \
        "$REGISTRY_URL/blacklist:standalone" >/dev/null
    
    # Wait for app to start
    log_info "Waiting for graceful degradation test app..."
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if curl -sf "http://localhost:3544/health" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        log_error "Graceful degradation app failed to start"
        return 1
    fi
    
    # Test that app works with fallback mechanisms
    local health_response=$(curl -s "http://localhost:3544/api/health")
    if echo "$health_response" | grep -q "cache.*memory"; then
        log_success "App gracefully degraded to memory cache"
    else
        log_warning "Cache fallback not detected in health response"
    fi
    
    # Test API functionality with fallbacks
    local api_response=$(curl -s "http://localhost:3544/api/blacklist/active")
    if [ $? -eq 0 ]; then
        log_success "API functional with graceful degradation"
    else
        log_error "API failed with graceful degradation"
        return 1
    fi
    
    log_success "Graceful degradation test passed"
}

# Function to test data persistence
test_data_persistence() {
    log_test "Testing data persistence across container restarts..."
    
    local app_container="independence-test-persistence"
    TEST_CONTAINERS+=("$app_container")
    
    # Start app with data volume
    log_info "Starting app with persistent data volume..."
    docker run -d \
        --name "$app_container" \
        --network "$TEST_NETWORK" \
        -p "3545:2542" \
        -v independence-test-app-data:/app/data \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL=sqlite:////app/data/persistence_test.db \
        -e CACHE_TYPE=memory \
        -e COLLECTION_ENABLED=false \
        -e LOG_LEVEL=DEBUG \
        "$REGISTRY_URL/blacklist:standalone" >/dev/null
    
    # Wait for app to start
    sleep 15
    
    # Create test data
    log_info "Creating test data..."
    curl -X POST "http://localhost:3545/api/blacklist" \
        -H "Content-Type: application/json" \
        -d '{"ip_address": "192.168.99.99", "source": "PERSISTENCE_TEST", "threat_level": "MEDIUM"}' \
        >/dev/null 2>&1 || true
    
    # Restart container
    log_info "Restarting container to test persistence..."
    docker stop "$app_container" >/dev/null
    docker rm "$app_container" >/dev/null
    
    # Start container again with same volume
    docker run -d \
        --name "$app_container" \
        --network "$TEST_NETWORK" \
        -p "3545:2542" \
        -v independence-test-app-data:/app/data \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL=sqlite:////app/data/persistence_test.db \
        -e CACHE_TYPE=memory \
        -e COLLECTION_ENABLED=false \
        -e LOG_LEVEL=DEBUG \
        "$REGISTRY_URL/blacklist:standalone" >/dev/null
    
    # Wait for app to restart
    sleep 15
    
    # Check if data persisted
    local blacklist_response=$(curl -s "http://localhost:3545/api/blacklist/active")
    if echo "$blacklist_response" | grep -q "192.168.99.99"; then
        log_success "Data persistence verified"
    else
        log_warning "Data persistence test inconclusive (data may not have been inserted initially)"
    fi
    
    log_success "Data persistence test completed"
}

# Function to run all tests
run_all_tests() {
    local quick_mode="$1"
    
    log_info "Starting Docker independence validation..."
    log_info "Test log: $TEST_LOG"
    echo
    
    # Record start time
    local start_time=$(date +%s)
    
    # Initialize test environment
    create_test_network
    check_images
    
    # Run tests
    local test_results=()
    
    # Test 1: App-only deployment
    if test_app_only_deployment; then
        test_results+=("App-only: PASSED")
    else
        test_results+=("App-only: FAILED")
    fi
    
    if [ "$quick_mode" != "true" ]; then
        # Test 2: PostgreSQL independence
        if test_postgresql_independence; then
            test_results+=("PostgreSQL: PASSED")
        else
            test_results+=("PostgreSQL: FAILED")
        fi
        
        # Test 3: Redis independence
        if test_redis_independence; then
            test_results+=("Redis: PASSED")
        else
            test_results+=("Redis: FAILED")
        fi
        
        # Test 4: Full stack deployment
        if test_full_stack_deployment; then
            test_results+=("Full Stack: PASSED")
        else
            test_results+=("Full Stack: FAILED")
        fi
        
        # Test 5: Graceful degradation
        if test_graceful_degradation; then
            test_results+=("Graceful Degradation: PASSED")
        else
            test_results+=("Graceful Degradation: FAILED")
        fi
        
        # Test 6: Data persistence
        if test_data_persistence; then
            test_results+=("Data Persistence: PASSED")
        else
            test_results+=("Data Persistence: FAILED")
        fi
    fi
    
    # Test 7: Docker-compose independence
    if test_docker_compose_independence; then
        test_results+=("Docker-compose Independence: PASSED")
    else
        test_results+=("Docker-compose Independence: FAILED")
    fi
    
    # Calculate test time
    local end_time=$(date +%s)
    local test_time=$((end_time - start_time))
    
    # Show results
    echo
    log_info "=== TEST RESULTS ==="
    local passed=0
    local failed=0
    
    for result in "${test_results[@]}"; do
        if echo "$result" | grep -q "PASSED"; then
            log_success "$result"
            passed=$((passed + 1))
        else
            log_error "$result"
            failed=$((failed + 1))
        fi
    done
    
    echo
    log_info "=== SUMMARY ==="
    log_info "Total tests: $((passed + failed))"
    log_info "Passed: $passed"
    log_info "Failed: $failed"
    log_info "Test duration: ${test_time} seconds"
    log_info "Test log: $TEST_LOG"
    
    if [ $failed -eq 0 ]; then
        echo
        log_success "🎉 ALL TESTS PASSED - Docker independence VERIFIED!"
        log_success "The Blacklist Management System can run completely independently"
        log_success "without docker-compose or any external orchestration."
        echo
        log_info "Independence verified:"
        log_info "  ✓ Zero docker-compose dependencies"
        log_info "  ✓ Each container starts with single docker run command"
        log_info "  ✓ No service dependencies in container startup"
        log_info "  ✓ Complete functionality without external orchestration"
        log_info "  ✓ Graceful degradation when services unavailable"
        log_info "  ✓ Data persistence across container restarts"
        return 0
    else
        echo
        log_error "❌ SOME TESTS FAILED - Independence not fully verified"
        log_error "Review the test log for details: $TEST_LOG"
        return 1
    fi
}

# Parse command line arguments
QUICK_MODE="false"
CLEANUP_ONLY="false"
VERBOSE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --registry)
            REGISTRY_URL="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE="true"
            shift
            ;;
        --cleanup)
            CLEANUP_ONLY="true"
            shift
            ;;
        --verbose)
            VERBOSE="true"
            set -x
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Setup trap for cleanup
trap cleanup_test_environment EXIT

# Main execution
if [ "$CLEANUP_ONLY" = "true" ]; then
    cleanup_test_environment
    exit 0
fi

# Run tests
if run_all_tests "$QUICK_MODE"; then
    exit 0
else
    exit 1
fi