#!/bin/bash
# Docker Independence Test Script
# Tests each container's ability to run independently
# Version: 1.0

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
TEST_NETWORK="blacklist-independence-test"
TEST_TIMEOUT=60
CLEANUP_CONTAINERS=()

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Cleanup function
cleanup() {
    log "Cleaning up test containers and network..."
    
    for container in "${CLEANUP_CONTAINERS[@]}"; do
        if docker ps -q -f name="$container" | grep -q .; then
            log "Stopping container: $container"
            docker stop "$container" >/dev/null 2>&1 || true
        fi
        if docker ps -aq -f name="$container" | grep -q .; then
            log "Removing container: $container"
            docker rm "$container" >/dev/null 2>&1 || true
        fi
    done
    
    if docker network ls | grep -q "$TEST_NETWORK"; then
        log "Removing test network: $TEST_NETWORK"
        docker network rm "$TEST_NETWORK" >/dev/null 2>&1 || true
    fi
}

# Setup trap for cleanup
trap cleanup EXIT

# Test PostgreSQL Independence
test_postgresql_independence() {
    log "Testing PostgreSQL container independence..."
    
    local container_name="test-postgresql-independent"
    CLEANUP_CONTAINERS+=("$container_name")
    
    # Run PostgreSQL container independently
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=blacklist_user \
        -e POSTGRES_PASSWORD=test_password_123 \
        -e PGDATA=/var/lib/postgresql/data/pgdata \
        "${REGISTRY_URL}/blacklist-postgresql:${IMAGE_TAG}" || {
        error "Failed to start independent PostgreSQL container"
        return 1
    }
    
    # Wait for container to be ready
    local attempt=0
    while [ $attempt -lt $TEST_TIMEOUT ]; do
        if docker exec "$container_name" pg_isready -U blacklist_user -d blacklist >/dev/null 2>&1; then
            log "PostgreSQL container is ready and independent"
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    
    error "PostgreSQL container failed independence test (timeout)"
    return 1
}

# Test Redis Independence
test_redis_independence() {
    log "Testing Redis container independence..."
    
    local container_name="test-redis-independent"
    CLEANUP_CONTAINERS+=("$container_name")
    
    # Run Redis container independently
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -e REDIS_MAXMEMORY=512mb \
        -e REDIS_MAXMEMORY_POLICY=allkeys-lru \
        "${REGISTRY_URL}/blacklist-redis:${IMAGE_TAG}" || {
        error "Failed to start independent Redis container"
        return 1
    }
    
    # Wait for container to be ready
    local attempt=0
    while [ $attempt -lt $TEST_TIMEOUT ]; do
        if docker exec "$container_name" redis-cli ping | grep -q "PONG"; then
            log "Redis container is ready and independent"
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    
    error "Redis container failed independence test (timeout)"
    return 1
}

# Test Main Application Independence
test_blacklist_independence() {
    log "Testing Blacklist application container independence..."
    
    local container_name="test-blacklist-independent"
    CLEANUP_CONTAINERS+=("$container_name")
    
    # Run Blacklist container independently with fallback config
    docker run -d \
        --name "$container_name" \
        --network "$TEST_NETWORK" \
        -p 12542:2542 \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL="sqlite:////app/instance/blacklist.db" \
        -e REDIS_URL="redis://fallback:6379/0" \
        -e CACHE_TYPE=memory \
        -e COLLECTION_ENABLED=false \
        -e FORCE_DISABLE_COLLECTION=true \
        -e SECRET_KEY=test_secret_key_independence \
        -e JWT_SECRET_KEY=test_jwt_secret_independence \
        -e API_KEY_ENABLED=false \
        -e JWT_ENABLED=false \
        "${REGISTRY_URL}/blacklist:${IMAGE_TAG}" || {
        error "Failed to start independent Blacklist container"
        return 1
    }
    
    # Wait for container to be ready
    local attempt=0
    while [ $attempt -lt $TEST_TIMEOUT ]; do
        if curl -sf "http://localhost:12542/health" >/dev/null 2>&1; then
            log "Blacklist container is ready and independent"
            
            # Test basic functionality
            local health_response=$(curl -s "http://localhost:12542/health")
            if echo "$health_response" | grep -q '"status":"healthy"'; then
                log "Blacklist container health check passed"
                return 0
            else
                warn "Blacklist container health check returned unexpected response: $health_response"
            fi
        fi
        sleep 2
        ((attempt++))
    done
    
    error "Blacklist container failed independence test (timeout)"
    docker logs "$container_name" | tail -20
    return 1
}

# Test Complete Stack Independence
test_complete_stack_independence() {
    log "Testing complete stack independence..."
    
    local pg_container="test-stack-postgresql"
    local redis_container="test-stack-redis"
    local app_container="test-stack-blacklist"
    
    CLEANUP_CONTAINERS+=("$pg_container" "$redis_container" "$app_container")
    
    # Start PostgreSQL
    docker run -d \
        --name "$pg_container" \
        --network "$TEST_NETWORK" \
        -e POSTGRES_DB=blacklist \
        -e POSTGRES_USER=blacklist_user \
        -e POSTGRES_PASSWORD=test_password_123 \
        "${REGISTRY_URL}/blacklist-postgresql:${IMAGE_TAG}"
    
    # Start Redis
    docker run -d \
        --name "$redis_container" \
        --network "$TEST_NETWORK" \
        "${REGISTRY_URL}/blacklist-redis:${IMAGE_TAG}"
    
    # Wait for databases
    sleep 10
    
    # Start Application with database connections
    docker run -d \
        --name "$app_container" \
        --network "$TEST_NETWORK" \
        -p 13542:2542 \
        -e FLASK_ENV=production \
        -e PORT=2542 \
        -e DATABASE_URL="postgresql://blacklist_user:test_password_123@${pg_container}:5432/blacklist" \
        -e REDIS_URL="redis://${redis_container}:6379/0" \
        -e CACHE_TYPE=redis \
        -e COLLECTION_ENABLED=false \
        -e SECRET_KEY=test_secret_key_stack \
        -e JWT_SECRET_KEY=test_jwt_secret_stack \
        "${REGISTRY_URL}/blacklist:${IMAGE_TAG}"
    
    # Wait for application
    local attempt=0
    while [ $attempt -lt $TEST_TIMEOUT ]; do
        if curl -sf "http://localhost:13542/health" >/dev/null 2>&1; then
            log "Complete stack is ready and independent"
            
            # Test database connectivity
            local health_response=$(curl -s "http://localhost:13542/api/health")
            if echo "$health_response" | grep -q '"database":"connected"'; then
                log "Database connectivity test passed"
            else
                warn "Database connectivity test failed"
            fi
            
            return 0
        fi
        sleep 2
        ((attempt++))
    done
    
    error "Complete stack failed independence test"
    return 1
}

# Main test execution
main() {
    log "Starting Docker Independence Tests"
    log "Registry: $REGISTRY_URL"
    log "Image Tag: $IMAGE_TAG"
    
    # Create test network
    if ! docker network ls | grep -q "$TEST_NETWORK"; then
        log "Creating test network: $TEST_NETWORK"
        docker network create "$TEST_NETWORK"
    fi
    
    local failed_tests=0
    
    # Run individual container tests
    log "=== Individual Container Independence Tests ==="
    
    if ! test_postgresql_independence; then
        ((failed_tests++))
    fi
    
    if ! test_redis_independence; then
        ((failed_tests++))
    fi
    
    if ! test_blacklist_independence; then
        ((failed_tests++))
    fi
    
    # Run complete stack test
    log "=== Complete Stack Independence Test ==="
    
    if ! test_complete_stack_independence; then
        ((failed_tests++))
    fi
    
    # Summary
    log "=== Test Summary ==="
    if [ $failed_tests -eq 0 ]; then
        log "✅ All independence tests passed!"
        log "All containers can run independently with 'docker run' commands"
        exit 0
    else
        error "❌ $failed_tests independence tests failed"
        error "Containers are not fully independent"
        exit 1
    fi
}

# Check if running as main script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi