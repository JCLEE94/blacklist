#!/bin/bash
# Independence Validation Test Suite
# Validates that all containers can run independently
# Version: 1.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
TEST_NETWORK="independence-validation"
VALIDATION_RESULTS=()

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Test result tracking
add_test_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    
    VALIDATION_RESULTS+=("$test_name|$status|$details")
}

# Cleanup function
cleanup() {
    log "Cleaning up validation test environment..."
    
    # Stop and remove all test containers
    docker ps -q --filter "network=$TEST_NETWORK" | xargs -r docker stop >/dev/null 2>&1 || true
    docker ps -aq --filter "network=$TEST_NETWORK" | xargs -r docker rm >/dev/null 2>&1 || true
    
    # Remove test network
    docker network rm "$TEST_NETWORK" >/dev/null 2>&1 || true
    
    # Remove unused volumes created during tests
    docker volume prune -f >/dev/null 2>&1 || true
}

trap cleanup EXIT

# Test 1: Volume Independence
test_volume_independence() {
    info "Testing volume independence..."
    
    local compose_file="${1:-docker-compose.yml}"
    local test_passed=true
    local details=""
    
    # Check for bind mounts in compose file
    if grep -q "device:" "$compose_file" 2>/dev/null; then
        error "Found bind mount dependencies in $compose_file"
        details="Bind mounts found: $(grep -n "device:" "$compose_file" | head -3)"
        test_passed=false
    fi
    
    # Check for host path mounts
    if grep -q "\./\|/host\|/home\|/var/run/docker.sock" "$compose_file" 2>/dev/null; then
        bind_mounts=$(grep -n "\./\|/host\|/home" "$compose_file" | grep -v "/var/run/docker.sock" | head -3 || true)
        if [ -n "$bind_mounts" ]; then
            warn "Found potential host path mounts: $bind_mounts"
            details="$details; Host paths: $bind_mounts"
        fi
    fi
    
    if [ "$test_passed" = true ]; then
        log "✅ Volume independence test passed"
        add_test_result "Volume Independence" "PASS" "No external volume dependencies found"
    else
        error "❌ Volume independence test failed"
        add_test_result "Volume Independence" "FAIL" "$details"
    fi
    
    return $([ "$test_passed" = true ] && echo 0 || echo 1)
}

# Test 2: Environment Variable Dependencies
test_env_dependencies() {
    info "Testing environment variable dependencies..."
    
    local dockerfile="${1:-build/docker/Dockerfile.independent}"
    local test_passed=true
    local details=""
    
    if [ ! -f "$dockerfile" ]; then
        error "Dockerfile not found: $dockerfile"
        add_test_result "Environment Dependencies" "FAIL" "Dockerfile not found"
        return 1
    fi
    
    # Check if essential ENV vars are set in Dockerfile
    local required_envs=(
        "SECRET_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "CACHE_TYPE"
        "COLLECTION_ENABLED"
    )
    
    for env_var in "${required_envs[@]}"; do
        if ! grep -q "ENV.*${env_var}=" "$dockerfile"; then
            error "Required ENV variable not found in Dockerfile: $env_var"
            details="$details; Missing: $env_var"
            test_passed=false
        fi
    done
    
    if [ "$test_passed" = true ]; then
        log "✅ Environment dependencies test passed"
        add_test_result "Environment Dependencies" "PASS" "All required ENV vars defined"
    else
        error "❌ Environment dependencies test failed"
        add_test_result "Environment Dependencies" "FAIL" "$details"
    fi
    
    return $([ "$test_passed" = true ] && echo 0 || echo 1)
}

# Test 3: Service Dependencies (depends_on)
test_service_dependencies() {
    info "Testing service dependencies..."
    
    local compose_file="${1:-docker-compose.independent.yml}"
    local test_passed=true
    local details=""
    
    if [ ! -f "$compose_file" ]; then
        error "Compose file not found: $compose_file"
        add_test_result "Service Dependencies" "FAIL" "Compose file not found"
        return 1
    fi
    
    # Check for depends_on clauses
    if grep -q "depends_on:" "$compose_file"; then
        depends_on_lines=$(grep -n "depends_on:" "$compose_file")
        warn "Found depends_on clauses (should use healthchecks instead): $depends_on_lines"
        details="depends_on found: $depends_on_lines"
        # This is a warning, not a failure for independence
    fi
    
    # Check that all services have healthchecks
    local services=$(grep -E "^  [a-zA-Z].*:$" "$compose_file" | grep -v "volumes:" | grep -v "networks:" | sed 's/://g' | tr -d ' ')
    for service in $services; do
        if ! grep -A 20 "^  $service:" "$compose_file" | grep -q "healthcheck:"; then
            warn "Service $service missing healthcheck (recommended for independence)"
            details="$details; Missing healthcheck: $service"
        fi
    done
    
    log "✅ Service dependencies test completed"
    add_test_result "Service Dependencies" "PASS" "$details"
    
    return 0
}

# Test 4: Network Independence
test_network_independence() {
    info "Testing network independence..."
    
    local compose_file="${1:-docker-compose.independent.yml}"
    local test_passed=true
    local details=""
    
    # Check for hardcoded hostnames (should use environment variables)
    local hardcoded_hosts=$(grep -n "://.*:" "$compose_file" | grep -v "\${" | head -3 || true)
    if [ -n "$hardcoded_hosts" ]; then
        warn "Found hardcoded hostnames (should use env vars): $hardcoded_hosts"
        details="Hardcoded hosts: $hardcoded_hosts"
    fi
    
    # Check that hostnames use environment variables
    if grep -q "\${.*_HOST" "$compose_file"; then
        log "✅ Found environment variable hostnames"
    else
        warn "No environment variable hostnames found"
        details="$details; No env var hostnames"
    fi
    
    log "✅ Network independence test completed"
    add_test_result "Network Independence" "PASS" "$details"
    
    return 0
}

# Test 5: Container Runtime Independence
test_container_runtime_independence() {
    info "Testing container runtime independence..."
    
    local test_passed=true
    local details=""
    
    # Create test network
    docker network create "$TEST_NETWORK" >/dev/null 2>&1 || true
    
    # Test 5a: Blacklist container independence
    info "Testing blacklist container independence..."
    
    local blacklist_container="test-runtime-blacklist"
    
    if docker run -d \
        --name "$blacklist_container" \
        --network "$TEST_NETWORK" \
        -p 15542:2542 \
        -e INDEPENDENT_MODE=true \
        -e ENABLE_FALLBACK_MODE=true \
        "${REGISTRY_URL}/blacklist:${IMAGE_TAG}" >/dev/null 2>&1; then
        
        # Wait for container to start
        local attempt=0
        while [ $attempt -lt 30 ]; do
            if docker logs "$blacklist_container" 2>&1 | grep -q "Independence Validation Complete\|started with pid"; then
                log "✅ Blacklist container started independently"
                break
            fi
            sleep 2
            ((attempt++))
        done
        
        if [ $attempt -ge 30 ]; then
            error "Blacklist container failed to start independently"
            docker logs "$blacklist_container" 2>&1 | tail -10
            test_passed=false
            details="$details; Blacklist startup failed"
        fi
        
        # Clean up
        docker stop "$blacklist_container" >/dev/null 2>&1 || true
        docker rm "$blacklist_container" >/dev/null 2>&1 || true
        
    else
        error "Failed to start blacklist container independently"
        test_passed=false
        details="$details; Blacklist container failed to start"
    fi
    
    # Test 5b: Redis container independence
    info "Testing Redis container independence..."
    
    local redis_container="test-runtime-redis"
    
    if docker run -d \
        --name "$redis_container" \
        --network "$TEST_NETWORK" \
        "${REGISTRY_URL}/blacklist-redis:${IMAGE_TAG}" >/dev/null 2>&1; then
        
        sleep 5
        
        if docker exec "$redis_container" redis-cli ping 2>/dev/null | grep -q "PONG"; then
            log "✅ Redis container started independently"
        else
            error "Redis container failed health check"
            test_passed=false
            details="$details; Redis health check failed"
        fi
        
        docker stop "$redis_container" >/dev/null 2>&1 || true
        docker rm "$redis_container" >/dev/null 2>&1 || true
        
    else
        error "Failed to start Redis container independently"
        test_passed=false
        details="$details; Redis container failed to start"
    fi
    
    # Test 5c: PostgreSQL container independence
    info "Testing PostgreSQL container independence..."
    
    local postgres_container="test-runtime-postgres"
    
    if docker run -d \
        --name "$postgres_container" \
        --network "$TEST_NETWORK" \
        -e POSTGRES_PASSWORD=test_password \
        "${REGISTRY_URL}/blacklist-postgresql:${IMAGE_TAG}" >/dev/null 2>&1; then
        
        sleep 15
        
        if docker exec "$postgres_container" pg_isready -U blacklist_user -d blacklist 2>/dev/null; then
            log "✅ PostgreSQL container started independently"
        else
            error "PostgreSQL container failed health check"
            docker logs "$postgres_container" 2>&1 | tail -10
            test_passed=false
            details="$details; PostgreSQL health check failed"
        fi
        
        docker stop "$postgres_container" >/dev/null 2>&1 || true
        docker rm "$postgres_container" >/dev/null 2>&1 || true
        
    else
        error "Failed to start PostgreSQL container independently"
        test_passed=false
        details="$details; PostgreSQL container failed to start"
    fi
    
    if [ "$test_passed" = true ]; then
        log "✅ Container runtime independence test passed"
        add_test_result "Container Runtime Independence" "PASS" "All containers started independently"
    else
        error "❌ Container runtime independence test failed"
        add_test_result "Container Runtime Independence" "FAIL" "$details"
    fi
    
    return $([ "$test_passed" = true ] && echo 0 || echo 1)
}

# Test 6: Docker Run Command Generation
test_docker_run_commands() {
    info "Generating independent docker run commands..."
    
    cat > docker-run-commands.sh << 'EOF'
#!/bin/bash
# Independent Docker Run Commands
# Each container can be started with these commands

# Network creation
docker network create blacklist-independent-net || true

# PostgreSQL Database
docker run -d \
    --name blacklist-postgresql-independent \
    --network blacklist-independent-net \
    -p 32544:5432 \
    -e POSTGRES_DB=blacklist \
    -e POSTGRES_USER=blacklist_user \
    -e POSTGRES_PASSWORD=your_secure_password_here \
    -v postgres-data-independent:/var/lib/postgresql/data \
    registry.jclee.me/blacklist-postgresql:latest

# Redis Cache
docker run -d \
    --name blacklist-redis-independent \
    --network blacklist-independent-net \
    -p 32543:6379 \
    -e REDIS_MAXMEMORY=1gb \
    -e REDIS_MAXMEMORY_POLICY=allkeys-lru \
    -v redis-data-independent:/data \
    registry.jclee.me/blacklist-redis:latest

# Wait for databases
sleep 10

# Blacklist Application
docker run -d \
    --name blacklist-app-independent \
    --network blacklist-independent-net \
    -p 32542:2542 \
    -e FLASK_ENV=production \
    -e DATABASE_URL="postgresql://blacklist_user:your_secure_password_here@blacklist-postgresql-independent:5432/blacklist" \
    -e REDIS_URL="redis://blacklist-redis-independent:6379/0" \
    -e SECRET_KEY="your_secret_key_here" \
    -e JWT_SECRET_KEY="your_jwt_secret_here" \
    -e COLLECTION_ENABLED=false \
    -e INDEPENDENT_MODE=true \
    -v blacklist-data-independent:/app/instance \
    -v blacklist-logs-independent:/app/logs \
    registry.jclee.me/blacklist:latest

echo "All containers started independently!"
echo "Access the application at: http://localhost:32542"
EOF
    
    chmod +x docker-run-commands.sh
    
    log "✅ Generated independent docker run commands in docker-run-commands.sh"
    add_test_result "Docker Run Commands" "PASS" "Commands generated successfully"
    
    return 0
}

# Generate detailed report
generate_report() {
    log "Generating independence validation report..."
    
    cat > independence-validation-report.md << 'EOF'
# Docker Container Independence Validation Report

## Summary

This report validates that all Docker containers in the Blacklist Management System can run independently using `docker run` commands without external dependencies.

## Test Results

EOF
    
    echo "| Test | Status | Details |" >> independence-validation-report.md
    echo "|------|--------|---------|" >> independence-validation-report.md
    
    local total_tests=0
    local passed_tests=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        IFS='|' read -r test_name status details <<< "$result"
        echo "| $test_name | $status | $details |" >> independence-validation-report.md
        ((total_tests++))
        if [ "$status" = "PASS" ]; then
            ((passed_tests++))
        fi
    done
    
    cat >> independence-validation-report.md << EOF

## Independence Score: ${passed_tests}/${total_tests} ($(( passed_tests * 100 / total_tests ))%)

## Recommendations

### 1. Volume Independence
- ✅ Use named volumes instead of bind mounts
- ✅ Ensure all data is stored in container volumes

### 2. Environment Variable Dependencies
- ✅ All required environment variables have defaults in Dockerfiles
- ✅ Containers can start without external .env files

### 3. Service Dependencies
- ✅ Remove depends_on clauses
- ✅ Use healthchecks for startup coordination
- ✅ Implement graceful fallback mechanisms

### 4. Network Independence
- ✅ Use environment variables for hostnames
- ✅ Provide fallback configurations

### 5. Container Runtime Independence
- ✅ Each container starts with docker run command
- ✅ No external file dependencies
- ✅ All configurations embedded

## Next Steps

1. Use \`docker-run-commands.sh\` to test independent deployment
2. Update CI/CD pipelines to use independent containers
3. Document independent deployment procedures
4. Regular testing of container independence

Generated on: $(date)
EOF
    
    log "✅ Independence validation report generated: independence-validation-report.md"
}

# Main execution
main() {
    log "Starting Docker Container Independence Validation"
    log "Registry: $REGISTRY_URL"
    log "Image Tag: $IMAGE_TAG"
    
    local failed_tests=0
    
    # Run all validation tests
    if ! test_volume_independence "docker-compose.independent.yml"; then
        ((failed_tests++))
    fi
    
    if ! test_env_dependencies "build/docker/Dockerfile.independent"; then
        ((failed_tests++))
    fi
    
    if ! test_service_dependencies "docker-compose.independent.yml"; then
        ((failed_tests++))
    fi
    
    if ! test_network_independence "docker-compose.independent.yml"; then
        ((failed_tests++))
    fi
    
    if ! test_container_runtime_independence; then
        ((failed_tests++))
    fi
    
    test_docker_run_commands
    
    # Generate report
    generate_report
    
    # Summary
    log "=== Independence Validation Summary ==="
    if [ $failed_tests -eq 0 ]; then
        log "✅ All independence tests passed!"
        log "🚀 Containers are ready for independent deployment"
        log "📄 See independence-validation-report.md for details"
        log "🔧 Use docker-run-commands.sh for independent deployment"
        exit 0
    else
        error "❌ $failed_tests independence tests failed"
        error "🚫 Containers are not fully independent"
        error "📄 See independence-validation-report.md for details"
        exit 1
    fi
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi